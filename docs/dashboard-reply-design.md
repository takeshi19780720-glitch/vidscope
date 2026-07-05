# ダッシュボード返信機能 — データモデル & API設計

## 1. 現状のスキーマ

`contacts` テーブル（`/Users/takeshikinoshita/Documents/Verdent/supabase_schema.sql`）:

```sql
create table if not exists contacts (
  id bigserial primary key,
  name text,
  email text,
  category text,
  message text,
  created_at timestamptz not null default now()
);
```

- 管理API: `GET /api/admin/contacts`, `DELETE /api/admin/contacts/{contact_id}` (`app/main.py`)
- 認証: `_require_admin()` — `X-Admin-Password` ヘッダーと `settings.admin_password` (`ADMIN_PASSWORD` 環境変数) を比較
- 既存のResend送信例: `_send_contact_email()` — `from: VidScope <reply@send.vidscope.app>` を使用（ドメイン認証済み）
- Supabaseアクセスは `app/supabase_client.py` の薄いPostgRESTラッパー経由（`select` / `insert` / `delete` / `rpc`）

## 2. データモデルの決定: Option B（新規 `contact_replies` テーブル）

**採用理由:**
- 1件の問い合わせに対して複数回の返信履歴を保持できる（再送・追記に対応）
- `contacts` テーブルの責務（受信データ）と返信履歴を分離し、既存の `SELECT *` 系クエリに影響を与えない
- 送信ステータス（pending/sent/failed）や失敗理由を記録でき、再送・監査が容易
- 将来的な拡張（複数管理者、返信テンプレート等）にも対応しやすい

Option A（`contacts` にカラム追加）は却下: 履歴管理ができず、返信のたびに上書きになるため監査性に欠ける。

## 3. SQLマイグレーション（`supabase_schema.sql` に追加済み）

```sql
-- お問い合わせへの管理者返信履歴（1件のcontactに対して複数回返信可能）
create extension if not exists pgcrypto;

create table if not exists contact_replies (
  id uuid primary key default gen_random_uuid(),
  contact_id bigint not null references contacts(id) on delete cascade,
  subject text not null,
  body text not null,
  status text not null default 'pending' check (status in ('pending', 'sent', 'failed')),
  error text,
  created_at timestamptz not null default now()
);
create index if not exists idx_contact_replies_contact_id on contact_replies(contact_id);
create index if not exists idx_contact_replies_created_at on contact_replies(created_at);

alter table contact_replies enable row level security;
```

- `id`: uuid（要件どおり `reply_id` として返却）
- `contact_id`: `contacts.id` への外部キー、`on delete cascade` で問い合わせ削除時に返信履歴も削除
- `status`: 送信結果を記録（Resend送信前に `pending` でinsertし、成否に応じて `sent`/`failed` に更新する運用を想定）
- `error`: 失敗時のエラーメッセージ保持用（任意）
- RLSは他テーブルと同様、ポリシー未追加でanon/authenticated経由のアクセスをデフォルト拒否（backendはservice_roleキーでバイパス）

## 4. FastAPI エンドポイント仕様

```
POST /api/admin/contacts/{contact_id}/reply
```

**認証:** 既存の `_require_admin(x_admin_password: str = Header(None))` をそのまま利用

**リクエストボディ:**
```json
{
  "subject": "string",
  "body": "string"
}
```

**レスポンス（成功時, HTTP 200）:**
```json
{ "success": true, "reply_id": "uuid" }
```

**レスポンス（失敗時, HTTP 200 または適切なエラーコード）:**
```json
{ "success": false, "error": "string" }
```

**処理フロー案:**
1. `_require_admin(x_admin_password)` で認証
2. `contact_id` に対応する `contacts` レコードを `supabase_client.select` で取得（存在しなければ404）
3. `subject` / `body` のバリデーション（空文字不可、長さ上限チェック）
4. `contact_replies` に `status='pending'` でinsert（`supabase_client.insert`）
5. Resend APIへ同期的に送信（管理者操作なのでレスポンスで成否を返す必要があるため、既存の問い合わせ通知のような非同期スレッドではなく同期呼び出しを推奨）
6. 送信成功 → `contact_replies.status` を `sent` に更新 → `{ "success": true, "reply_id": ... }` を返す
7. 送信失敗 → `status` を `failed`、`error` にメッセージを記録 → `{ "success": false, "error": "..." }` を返す（HTTPステータスは502等でも可、フロント側の扱いに合わせる）

**想定コード骨格（実装時の参考、Step 2用）:**
```python
class ReplyRequest(BaseModel):
    subject: str
    body: str

@app.post("/api/admin/contacts/{contact_id}/reply")
def reply_to_contact(contact_id: int, payload: ReplyRequest, x_admin_password: str = Header(None)):
    _require_admin(x_admin_password)

    contacts = supabase_client.select("contacts", select="id,email,name", filters={"id": f"eq.{contact_id}"})
    if not contacts:
        raise HTTPException(status_code=404, detail="お問い合わせが見つかりません")
    contact = contacts[0]

    if not payload.subject.strip() or not payload.body.strip():
        raise HTTPException(status_code=400, detail="件名と本文を入力してください")

    reply_row = supabase_client.insert("contact_replies", {
        "contact_id": contact_id,
        "subject": payload.subject,
        "body": payload.body,
        "status": "pending",
    })
    if not reply_row:
        return {"success": False, "error": "返信履歴の保存に失敗しました"}

    reply_id = reply_row["id"]
    ok, err = _send_reply_email(contact["email"], payload.subject, payload.body)

    supabase_client.update... # status を sent/failed に更新（PATCHメソッドをsupabase_clientに追加する必要あり）

    if not ok:
        return {"success": False, "error": err}
    return {"success": True, "reply_id": reply_id}
```

> 注: `supabase_client.py` には現状 `update`/`patch` 関数がないため、Step 2実装時に `PATCH` ラッパーの追加が必要（`select`/`insert`/`delete`と同様のパターン）。

## 5. Resend メールペイロード

```json
{
  "from": "VidScope <reply@send.vidscope.app>",
  "to": ["<contact.email>"],
  "subject": "<provided subject>",
  "text": "<provided body>"
}
```

- 送信元は既存の `_send_contact_email()` と同一（ドメイン認証済みの `send.vidscope.app`）
- `to` は対象 `contacts.email`（配列形式、既存実装に準拠）
- 既存実装との違い: 管理者向け通知ではなく問い合わせ者本人への返信のため `reply_to` は不要（省略可、必要なら `NOTIFY_EMAIL` を設定してもよい）
- タイムアウトは既存と同じ `timeout=10` を踏襲

## 6. エラーケース & レート制限

**エラーケース:**
| ケース | 対応 |
|---|---|
| `contact_id` が存在しない | HTTP 404 |
| 認証失敗（パスワード不一致） | HTTP 401（既存 `_require_admin` の挙動を継承） |
| `subject`/`body` が空 | HTTP 400 |
| Resend APIキー未設定 | `{ "success": false, "error": "メール送信設定が未構成です" }`（既存 `_send_contact_email` の `RESEND_API_KEY` チェックに準拠） |
| Resend API呼び出し失敗（非200） | `contact_replies.status='failed'` に更新し `{ "success": false, "error": "..." }` を返す |
| Supabase書き込み失敗 | `{ "success": false, "error": "返信履歴の保存に失敗しました" }`、メール送信は行わない（履歴なしの送信を避ける） |

**レート制限:**
- 既存の `slowapi` (`Limiter`) を流用し、`@limiter.limit("10/minute")` 程度を管理者エンドポイントに付与（管理者は少人数運用のため緩やかな制限で十分）
- 目的は誤操作による連続送信・Resend側のレート超過防止（Resendの送信レート上限に対する保護）
- 既存の `/api/search` エンドポイントと同じパターン（`request: Request` を引数に追加し `@limiter.limit(...)` デコレータを付与）で実装可能

## 7. まとめ（Step 2実装時のTODO）

1. `supabase_schema.sql` に `contact_replies` テーブルを追加済み（本ドキュメントの通り）
2. `app/supabase_client.py` に `update`/`patch` 関数を追加（`contact_replies.status` 更新用）
3. `app/main.py` に `POST /api/admin/contacts/{contact_id}/reply` エンドポイントを追加
4. Resend送信ロジック `_send_reply_email()` を `_send_contact_email()` と同パターンで実装
5. レート制限デコレータを追加
6. フロントエンド（管理ダッシュボード）に返信フォームUIを追加（本タスクのスコープ外）

# Flask ToDo App (CLI + UI)

軽量なToDoアプリです。Python標準ライブラリのJSONで永続化し、
- CLIツール（`todo.py`）
- Flask製モダンUI（`app.py` + `templates/`）
を同梱しています。外部DB不要で手軽に使えます。

## 特長
- シンプルなJSONストレージ（`todos.json`）
- 期日（YYYY-MM-DD）と完了状態の管理
- UIはBootstrap 5利用（CDN）
- 期限超過のハイライト、統計表示（合計/未完了/完了/期限切れ）

## クイックスタート
1) 依存インストール
```
python -m pip install -r requirements.txt
```

2) 開発サーバ起動
```
python app.py
# ブラウザ: http://127.0.0.1:5000/
```

3) CLIの例
```
python todo.py add "牛乳を買う" --due 2025-09-01
python todo.py list --all
python todo.py done 1
python todo.py edit 1 --title "オートミルク" --clear-due
python todo.py delete 1
python todo.py stats
```

`todos.json` はスクリプトと同じディレクトリに作成されます（`.gitignore` 済み）。

## プロジェクト構成
```
app.py                 # Flaskアプリ
templates/
  base.html
  index.html
  edit.html

todo.py                # CLI/ストレージロジック
requirements.txt       # 依存パッケージ（Flask）
```

## 開発メモ
- Python: 3.8+（Flask 3系対応）
- UI: Bootstrap (CDN) + Bootstrap Icons (CDN)
- PRGパターン採用（POST後はリダイレクト）
- `@app.context_processor` で `stats` を全テンプレートに注入

## CI（GitHub Actions）
- 変更をプッシュすると、依存インストールと簡易Lint/Formatチェック（flake8 / black --check）を実行します。
- ローカルでも `pip install black flake8` 後、`black .` / `flake8` で確認できます。

## ライセンス
このリポジトリには明示的なライセンスを含めていません。公開/配布の方針が決まり次第追加してください。

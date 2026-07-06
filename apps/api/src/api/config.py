from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = (
        "postgresql+asyncpg://postgres:postgres@localhost:5442/seminar_platform"
    )
    slack_bot_token: str | None = None

    # --- 認証(JWT検証) ---
    # フロント(Auth.js)が発行したJWTを検証するための設定。
    # JWKSのURL・想定するissuer/audienceを .env から受け取る(#6 の発行側と対応)。
    jwt_jwks_url: str = ""
    jwt_issuer: str = ""
    jwt_audience: str = ""

    # --- 開発用ダミー認証 ---
    # true のときだけ実JWT検証を行わず、X-Dev-User-Email ヘッダのユーザーとして
    # 認証する(未指定なら auth_dev_user_email)。ローカル/CI専用。本番は必ず false。
    auth_dev_mode: bool = False
    auth_dev_user_email: str = "dev-student@example.com"

    # --- CORS ---
    # ブラウザ(apps/web)から直接叩けるようにするオリジン。slack-botと共有の
    # WEB_APP_URL(ブラウザから見えるURL)をそのまま使う(#42)。
    # CORSのOriginヘッダは末尾スラッシュを含まないため、比較がズレないよう正規化する。
    web_app_url: str = "http://localhost:3100"

    @field_validator("web_app_url")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

    # --- web-api間シークレット ---
    # ログイン前(未認証)に呼ぶ必要がありJWT検証を通せないエンドポイント
    # (/users/exists 等)を、web以外からの直接アクセスから守るための合言葉。
    internal_api_secret: str = ""


settings = Settings()

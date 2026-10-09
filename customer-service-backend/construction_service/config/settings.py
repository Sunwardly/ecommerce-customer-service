"""
.env中的信息 收集到配置类中
"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT_DIR = Path(__file__).resolve().parents[2]
ENV_FILE_PATH = PROJECT_ROOT_DIR / ".env"


class Settings(BaseSettings):
    """Load private configuration from environment or the local .env file."""
    llm_model: str  # 类型str,且是必填参数
    llm_base_url: str
    llm_api_key: str
    commerce_api_base_url: str
    database_url: str
    app_host: str
    app_port: int

    # 万相数字人(灵眸) 云渲染. 说话由灵眸服务端 TTS 完成
    avatar_access_key_id: str = ""
    avatar_access_key_secret: str = ""
    avatar_endpoint: str = "lingmou.cn-beijing.aliyuncs.com"
    avatar_project_id: str = ""
    avatar_instance_id: str = ""

    model_config=SettingsConfigDict(env_file=ENV_FILE_PATH, env_file_encoding="utf-8", extra="ignore")  # extra="ignore"


settings = Settings()  # type: ignore

if __name__ == '__main__':
    print(settings.llm_base_url)

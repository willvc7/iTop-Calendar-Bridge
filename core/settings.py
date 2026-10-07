import yaml
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import ValidationError, PrivateAttr
from loguru import logger
from core.files import display_path
from core.paths import writable_root

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="ITOPCB_", env_ignore_empty=True)
    # --- 公開設定欄位 ---
    headless: bool = True
    username: str = ""
    itop_url: str = ""
    create_TimeSpent: str = "c[menu]=MyTimeTrackingReport&operation=new&class=TimeSpent"
    request_list: str = "c[menu]=internal:Requestassignedtome, c[menu]=internal:Requestscreatedbymyself, c[menu]=UserRequest:Requests_assigned_to_me-2"
    file_encoding: str = "utf-8-sig"
    required_fields: str = "Request, Date, StartTime, EndTime, Description"
    
    # --- 個人化選項 ---
    send_mail: bool = False
    send_cache_mail: bool = False
    calendar_output: str = "data/raw_calendar.csv"
    calendar_start: str = ""
    calendar_end: str = ""
    request_cache: str = "data/itop_data.json"
    upload_input: str = "iTop.csv"

    # --- 內部私有屬性 ---
    _config_path: Path = PrivateAttr()

    @classmethod
    def load_settings(cls) -> "Settings":
        """單一來源 config/config.yaml。
        """

        repo_config = writable_root() / "config" / "config.yaml"
        repo_config.parent.mkdir(parents=True, exist_ok=True)

        try:
            if repo_config.exists():
                with open(repo_config, "r", encoding="utf-8-sig") as f:
                    on_disk = yaml.safe_load(f) or {}

                defaults = cls().model_dump()
                missing = {k: v for k, v in defaults.items() if k not in on_disk}
                if missing:
                    on_disk.update(missing)
                    with open(repo_config, "w", encoding="utf-8") as f:
                        yaml.dump(on_disk, f, allow_unicode=True, sort_keys=False)
                instance = cls(**on_disk)
            else:
                logger.info("首次執行，正在建立預設設定檔...")
                instance = cls()
        except ValidationError as e:
            logger.warning(f"設定檔版本不相容，將使用預設值。錯誤: {e}")
            instance = cls()

        instance._config_path = repo_config
        if not repo_config.exists():
            instance.save()

        return instance

    def save(self):
        """將目前的設定狀態寫回 YAML 檔案"""
        try:
            data = self.model_dump()
            with open(self._config_path, "w", encoding="utf-8") as f:
                yaml.dump(data, f, allow_unicode=True, sort_keys=False)
            logger.trace(f"設定已成功儲存至: {display_path(self._config_path)}")
        except Exception as e:
            logger.error(f"儲存設定檔時發生錯誤: {e}")

    @property
    def config_path(self) -> Path:
        """提供一個唯讀屬性，讓外部程式可以知道設定檔在哪裡"""
        return self._config_path

    def resolve(self, p: str) -> Path:
        """相對路徑以可寫入根目錄為基準轉絕對路徑（原始碼模式即 repo 根目錄）"""
        path = Path(p)
        if path.is_absolute():
            return path
        return writable_root() / p

    def resolve_request_cache(self) -> Path:
        """單一來源 settings.request_cache（預設 data/itop_data.json）"""
        return self.resolve(self.request_cache)

    def resolve_upload_input(self, override: str = "") -> Path:
        """CLI 指定 > 設定值 > 新舊路徑備援"""
        candidates: list[Path] = []
        if override:
            candidates.append(self.resolve(override))
        candidates.append(self.resolve(self.upload_input))
        candidates.append(writable_root() / "data" / "raw_calendar.csv")
        candidates.append(writable_root() / "iTop.csv")
        for c in candidates:
            if c.exists():
                return c
        return candidates[1] if len(candidates) > 1 else writable_root() / "iTop.csv"

settings = Settings.load_settings()
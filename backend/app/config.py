from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Job Hunter API"
    app_env: str = "development"
    database_url: str = "sqlite:///./ai_job_hunter.db"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    auto_submit_enabled: bool = False
    application_browser_profile_dir: str = "data/browser-profile"
    ai_provider: str = "ollama"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "qwen2.5:3b-instruct"
    semantic_matching_enabled: bool = True
    ollama_embedding_model: str = "nomic-embed-text"
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    adzuna_app_id: str = ""
    adzuna_app_key: str = ""
    brave_search_api_key: str = ""
    # JobSpy is an opt-in scraping connector; disabled until explicitly enabled by the user.
    jobspy_enabled: bool = False
    jobspy_sites: str = "linkedin,indeed,naukri,glassdoor,zip_recruiter,bayt,bdjobs,hellowork"
    jobspy_max_searches: int = 6
    jobspy_results_wanted: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    @property
    def cors_origin_list(self) -> list[str]:
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]


settings = Settings()

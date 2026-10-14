"""起動スクリプト。127.0.0.1 のみで待ち受ける(外部公開は Tailscale Serve 経由)。"""
import logging
import sys

import uvicorn

from app.config import install_log_redaction, load_settings
from app.main import create_app


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    install_log_redaction()
    settings = load_settings()
    try:
        app = create_app(settings, start_background=True)
    except RuntimeError as e:
        print(f"起動できません: {e}", file=sys.stderr)
        sys.exit(1)
    # host は固定。0.0.0.0 にしないこと
    uvicorn.run(app, host="127.0.0.1", port=settings.port, log_level="info", access_log=False)


if __name__ == "__main__":
    main()

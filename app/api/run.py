import logging

import uvicorn

from ..core.config import config


logging.basicConfig(
        level=config.logging.log_level_value,
        format=config.logging.log_format
)

if __name__ == '__main__':
    uvicorn.run('app.api.main:main_app', host=config.run.host, port=config.run.port, reload=config.api.debug)

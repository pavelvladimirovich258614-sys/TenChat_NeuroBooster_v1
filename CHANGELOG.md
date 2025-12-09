# Changelog

All notable changes to TenChat NeuroBooster will be documented in this file.

## [1.1.0] - 2025-12-09

### Added
- **SOCKS5 Proxy Support**: Full support for SOCKS5 proxies via httpx-socks library
  - Support for multiple proxy formats: `socks5://ip:port:user:pass`, `socks5:ip:port:user:pass`, `ip:port:user:pass`
  - Automatic proxy type detection (HTTP/SOCKS5)
  - Proxy type indicator in UI ([HTTP] or [SOCKS5])
- **TenChat-specific Cookies Support**: Added recognition for TenChat cookies (SESSION, TCAF, TCRF)
- **Detailed Error Messages**: Improved error handling with specific messages for proxy, connection, and validation errors
- **Debug Logging**: Added comprehensive logging for cookies parsing and validation

### Fixed
- Fixed "500 Internal Server Error" when adding accounts with SOCKS5 proxy
- Fixed "Invalid cookies" error for valid Cookie-Editor exports with TenChat cookies
- Fixed proxy validation to properly handle both HTTP and SOCKS5 formats
- Fixed cookies validation to be case-insensitive (SESSION, session, Session all valid)

### Changed
- Updated ProxyHandler to support both HTTP and SOCKS5 proxy types
- Updated TenChatClient to use httpx-socks for SOCKS5 connections
- Enhanced cookies_parser with TenChat-specific cookie names
- Improved error messages throughout the API for better debugging

### Documentation
- Updated README.md with SOCKS5 proxy examples and formats
- Added troubleshooting section for proxy issues
- Added instructions for Cookie-Editor usage

## [1.0.0] - 2025-12-09

### Added
- Initial release of TenChat NeuroBooster
- Account management system with cookies-based authentication
- Proxy support (1 account = 1 proxy architecture)
- TenChat API wrapper with HTTP/2 support
- AI content generator with OpenAI-compatible API integration
- Task executor with human emulation (random delays 60-180s)
- Safety limits: 50 likes/day, 20 follows/day, 2 posts/day
- Warmup mode (automatic feed liking)
- AI Post mode (automatic article generation and posting)
- Streamlit UI with 3 tabs (Accounts, Tasks, Logs)
- FastAPI backend with async task queue
- SQLite database for accounts, tasks, actions, and stats
- Docker Compose deployment
- Comprehensive README with setup instructions

### Features
- Multi-account support
- User-Agent generation and fingerprinting
- Daily statistics tracking
- Action logging with success/error tracking
- Real-time task progress monitoring
- Background task worker
- Health checks and status monitoring

### Security
- Cookies validation
- Proxy validation and formatting
- Daily limits enforcement
- Error handling for expired cookies and captcha
- Automatic account status management

### Tech Stack
- Python 3.11+
- FastAPI
- Streamlit
- SQLAlchemy (async)
- httpx (HTTP/2)
- SQLite
- Docker Compose
- OpenAI Python SDK

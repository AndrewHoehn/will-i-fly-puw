# Security Policy

## Reporting a Vulnerability

We take security seriously at Will I Fly PUW. If you discover a security vulnerability, please follow these steps:

### How to Report

**Please do NOT report security vulnerabilities through public GitHub issues.**

Instead, please report them via one of the following methods:

1. **GitHub Security Advisories** (Preferred)
   - Navigate to the repository's Security tab
   - Click "Report a vulnerability"
   - Fill out the security advisory form

2. **Email**
   - Send details to the repository maintainer
   - Include "SECURITY" in the subject line
   - Provide a detailed description of the vulnerability

### What to Include

When reporting a vulnerability, please include:

- Type of vulnerability (e.g., SQL injection, XSS, authentication bypass)
- Full paths of affected source files
- Location of the affected code (tag/branch/commit or direct URL)
- Step-by-step instructions to reproduce the issue
- Proof-of-concept or exploit code (if possible)
- Impact assessment of the vulnerability

### Response Timeline

- **Initial Response**: Within 48 hours of report submission
- **Status Update**: Within 7 days with initial assessment
- **Fix Timeline**: Dependent on severity, typically 30-90 days
- **Public Disclosure**: After fix is deployed and verified

## Security Best Practices

### For Contributors

When contributing to this project:

1. **Never commit sensitive data**:
   - API keys, passwords, or tokens
   - Production database credentials
   - Private keys or certificates

2. **Follow secure coding practices**:
   - Validate and sanitize all user inputs
   - Use parameterized queries to prevent SQL injection
   - Implement proper authentication and authorization
   - Keep dependencies up to date

3. **Review `.gitignore`**:
   - Ensure `.env` files are excluded
   - Check that database files aren't committed
   - Verify log files are ignored

### For Deployers

When deploying this application:

1. **Environment Variables**:
   - Use Fly.io secrets or environment variables for API keys
   - Never hardcode credentials in source code
   - Rotate API keys periodically

2. **Database Security**:
   - Ensure SQLite database file has proper permissions
   - Use persistent volumes for production data
   - Implement regular backups

3. **API Security**:
   - Consider rate limiting for public endpoints
   - Monitor for unusual traffic patterns
   - Keep FastAPI and dependencies updated

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

## Known Security Considerations

### API Keys
This application requires external API keys:
- **AeroDataBox** (via RapidAPI)
- **AviationStack**

These should be stored securely as environment variables, never committed to version control.

### Public Data
All flight data displayed is publicly available information sourced from:
- FAA flight data APIs
- Open-Meteo weather API
- Bureau of Transportation Statistics

No personally identifiable information (PII) is collected or stored.

### Rate Limiting
The application currently does not implement rate limiting on its API endpoints. This is acceptable for personal/small-scale deployments but should be considered for high-traffic scenarios.

## Security Updates

We will:
- Monitor dependencies for known vulnerabilities
- Apply security patches promptly
- Notify users of critical security updates via GitHub releases

## Acknowledgments

We thank security researchers who responsibly disclose vulnerabilities to us. Contributors who report valid security issues will be acknowledged in our release notes (unless they prefer to remain anonymous).

# Security Policy

## Supported Versions

We release patches for security vulnerabilities for the following versions:

| Version | Supported          |
| ------- | ------------------ |
| main    | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

If you discover a security vulnerability, please send an email to the maintainers with:

1. Description of the vulnerability
2. Steps to reproduce
3. Potential impact
4. Suggested fix (if any)

### What to Expect

- **Acknowledgment**: Within 48 hours
- **Initial Assessment**: Within 1 week
- **Fix Timeline**: Depends on severity (critical issues within days, others within weeks)
- **Disclosure**: After a fix is released, we'll publicly disclose the vulnerability

## Security Best Practices

When using ToastyAnalytics in production:

1. **Use Environment Variables**: Never commit secrets to git
2. **Enable JWT Authentication**: Secure all API endpoints
3. **Use HTTPS**: Always use TLS in production
4. **Update Dependencies**: Regularly update to latest versions
5. **Enable Rate Limiting**: Protect against abuse
6. **Monitor Logs**: Watch for suspicious activity
7. **Database Security**: Use strong passwords and restrict access
8. **Container Security**: Scan Docker images for vulnerabilities

## Known Security Considerations

- API keys should be rotated regularly
- JWT tokens have configurable expiration times
- Rate limiting is configurable per endpoint
- Database credentials should use strong passwords
- Redis should be password-protected in production

Thank you for helping keep ToastyAnalytics secure!

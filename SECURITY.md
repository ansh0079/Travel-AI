# Security Policy

## Reporting a Vulnerability

We take the security of TravelAI seriously. If you discover a security vulnerability, please report it responsibly.

**Please DO NOT open a public issue for security vulnerabilities.**

Instead, please report them by:
1. Creating a draft security advisory in the repository (if you have maintainer access)
2. Or contacting the maintainers directly

## Security Best Practices

### For Developers

#### Environment Variables
- **NEVER** commit `.env` files with real credentials
- Use `.env.example` as a template
- Rotate keys immediately if accidentally committed

#### Required Environment Variables
The following variables MUST be set in production:
- `SECRET_KEY` - At least 32 characters, cryptographically random
- `DATABASE_URL` - Use PostgreSQL, not SQLite
- All API keys for external services

#### Secret Key Generation
```bash
# Generate a secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

#### Database
- Use PostgreSQL for production (SQLite is development-only)
- Never use default credentials in production
- Enable SSL for database connections in production

#### API Keys
- Use environment-specific keys (dev, staging, production)
- Rotate keys regularly
- Use minimal required permissions

### Rate Limiting

The application includes rate limiting to prevent abuse:
- Default: 100 requests per minute per IP
- Auth endpoints have stricter limits

### Input Validation

All API endpoints include input validation:
- String length limits
- Pattern validation for IDs
- Type checking for numbers and dates

### Authentication

- JWT tokens expire after 24 hours (configurable)
- Passwords must be at least 8 characters
- Passwords are hashed with bcrypt

### CORS

- Configure `ALLOWED_ORIGINS` for your specific domains
- Do not use wildcards in production

## Security Checklist for Deployment

- [ ] `SECRET_KEY` is set and at least 32 characters
- [ ] Using PostgreSQL, not SQLite
- [ ] All default passwords changed
- [ ] `ALLOWED_ORIGINS` configured for production domains
- [ ] Debug mode disabled (`DEBUG=false`)
- [ ] HTTPS enabled
- [ ] Database backups configured
- [ ] API keys rotated from defaults
- [ ] Rate limiting enabled
- [ ] Logging configured (no sensitive data in logs)

## Dependencies

Keep dependencies up to date:
```bash
# Check for outdated packages
pip list --outdated
npm outdated

# Update dependencies
pip install --upgrade -r requirements.txt
npm update
```

## Security Headers

The application should be deployed with these headers:
- `Strict-Transport-Security`
- `X-Content-Type-Options: nosniff`
- `X-Frame-Options: DENY`
- `X-XSS-Protection: 1; mode=block`

## Logging

- Sensitive data (passwords, tokens) is never logged
- Use structured logging in production
- Monitor logs for suspicious activity

## Known Limitations

1. **SQLite in Development**: The default database is SQLite, which is not suitable for production due to concurrency limitations.

2. **Mock Data**: Some services fall back to mock data when API keys are not provided. This is intentional for development but should be configured properly in production.

## Security Updates

Security patches will be released as soon as possible. Check the changelog for security-related updates.

## Third-Party Services

This application integrates with several third-party services. Review their security policies:
- OpenAI (AI recommendations)
- OpenWeatherMap (Weather data)
- Amadeus (Flight data)
- Google Places (Attractions)
- Ticketmaster (Events)

## Contact

For security concerns, please contact the maintainers through the repository.

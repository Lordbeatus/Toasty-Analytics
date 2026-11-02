# Security policy

## Supported versions

Security fixes are applied to `main`. Older snapshots are not maintained.

## Reporting a vulnerability

Do not open a public issue for a security problem. Use GitHub's private
vulnerability reporting on
[the repository](https://github.com/Lordbeatus/Toasty-Analytics/security/advisories/new),
or contact the maintainer directly if that is unavailable.

Include:

- a description of the issue and its impact
- steps to reproduce, or a proof of concept
- affected versions or commits
- any suggested remediation

You can expect an acknowledgement within 48 hours, an assessment within a week,
and a fix or mitigation plan for confirmed issues. Please allow time for a fix
before public disclosure.

## Deployment guidance

The default configuration is intended for local development. Before exposing an
instance publicly:

1. **Add authentication.** The default FastAPI app does not require
   authentication. Put it behind an authenticating proxy or wire
   `toastyanalytics/auth/jwt_auth.py` into the application.
2. **Use TLS.** Terminate HTTPS at a proxy or load balancer.
3. **Protect credentials.** Keep `TOASTYANALYTICS_DB_URL`, `SENTRY_DSN`, and
   `JWT_SECRET_KEY` in environment variables or a secret manager, never in Git.
4. **Restrict the database and Redis.** Use strong passwords, private networks,
   and no public port exposure.
5. **Set a real JWT secret.** `jwt_auth.py` falls back to a placeholder key when
   `JWT_SECRET_KEY` is unset; the placeholder is not safe for production.
6. **Update dependencies.** Dependabot or a scheduled `pip list --outdated`
   review keeps the stack current.
7. **Review CORS.** The API allows all origins by default, which is convenient
   locally and too permissive for a public deployment.

## Known limitations

- The default app exposes grading and analytics endpoints without
  authorization.
- Rate limiting exists as a helper module but is not enabled by default.
- Error tracking is only active when `sentry-sdk` is installed and
  `SENTRY_DSN` is set.

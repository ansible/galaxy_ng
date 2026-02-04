# Dynamic Hostname Settings

Galaxy NG provides dynamic hostname configuration through the `alter_hostname_settings` function, which automatically adjusts hostname-related settings based on HTTP request headers. This is essential for deployments behind reverse proxies, load balancers, or in multi-tier architectures.

## Overview

The dynamic hostname system automatically modifies these settings based on incoming request headers:

- `CONTENT_ORIGIN` - The base URL for content serving
- `ANSIBLE_API_HOSTNAME` - The hostname for Ansible API endpoints  
- `TOKEN_SERVER` - The token server URL (automatically appends `/token/`)

## Configuration

### Enabling Dynamic Hostname Settings

Add the hook to your configuration:

```python
DYNACONF_AFTER_GET_HOOKS = [
    "alter_hostname_settings"
]
```

### Resource Server Mode

When connected to a resource server, strict header validation is enforced:

In this mode, proper forwarded headers become **mandatory** for web requests.

## Supported Header Formats

### X-Forwarded Headers (Recommended)

The most common format used by reverse proxies:

```http
X-Forwarded-Proto: https
X-Forwarded-Host: galaxy.example.com
```

Or with the standard Host header:

```http
X-Forwarded-Proto: https
Host: galaxy.example.com
```

### RFC 7239 Forwarded Header (Fallback)

Standards-compliant format as defined in [RFC 7239](https://datatracker.ietf.org/doc/html/rfc7239):

```http
Forwarded: proto=https;host=galaxy.example.com
```

Complex example with additional parameters:

```http
Forwarded: for=192.0.2.60;proto=https;by=203.0.113.43;host=api.galaxy.com
```

### Header Priority

The system processes headers in this priority order:

1. **X-Forwarded-Proto** + **X-Forwarded-Host** (highest priority)
2. **X-Forwarded-Proto** + **Host** header
3. **RFC 7239 Forwarded** header (fallback)
4. **Request protocol** (`req.is_secure()`) + **Host** header

## Deployment Scenarios

### Standard Deployment

Direct access without reverse proxy:

```yaml
# No special headers required
# Uses request protocol and Host header
Request: https://galaxy.example.com/api/v3/
Result: CONTENT_ORIGIN = "https://galaxy.example.com"
```

### Behind Reverse Proxy

Typical reverse proxy setup with header forwarding:

```nginx
# Nginx configuration
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header Host $host;
```

```yaml
Request Headers:
  X-Forwarded-Proto: https
  X-Forwarded-Host: api.galaxy.com
  
Result: CONTENT_ORIGIN = "https://api.galaxy.com"
```

### Load Balancer with RFC 7239

Modern load balancers supporting RFC 7239:

```yaml
Request Headers:
  Forwarded: proto=https;host=api.galaxy.com;for=203.0.113.195
  
Result: CONTENT_ORIGIN = "https://api.galaxy.com"
```

### Resource Server Connected

When connected to a resource server, headers become mandatory:

```yaml
# ✅ Valid - Headers present
Request Headers:
  X-Forwarded-Proto: https
  Host: galaxy.example.com
Result: CONTENT_ORIGIN = "https://galaxy.example.com"

# ❌ Invalid - Missing protocol header
Request Headers:
  Host: galaxy.example.com
Result: HTTP 400 Bad Request - SuspiciousOperation
```

## Error Handling

### Missing Headers in Resource Server Mode

When connected to a resource server and required headers are missing:

```python
# Raises django.core.exceptions.SuspiciousOperation (HTTP 400)
# Error message includes specific requirements:
"alter_hostname_settings: When connected to resource server, both protocol and host 
must be provided in headers. Found proto='None', host='galaxy.example.com'. 
Required headers: X-Forwarded-Proto + (X-Forwarded-Host or Host), 
or RFC 7239 Forwarded header with proto and host parameters."
```

### Script/CLI Access

When accessing settings from management commands or scripts (no HTTP request context):

```python
# Django management command
from django.conf import settings
print(settings.CONTENT_ORIGIN)  # Returns original configured value
```

The function gracefully returns the original configured value when no request context is available.

## Proxy Configuration Examples

### Nginx

```nginx
server {
    listen 443 ssl;
    server_name galaxy.example.com;
    
    location / {
        proxy_pass http://backend:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header X-Forwarded-Host $host;
    }
}
```

### Apache

```apache
<VirtualHost *:443>
    ServerName galaxy.example.com
    
    ProxyPass / http://backend:8000/
    ProxyPassReverse / http://backend:8000/
    
    ProxyPreserveHost On
    ProxyAddHeaders On
    
    Header always set X-Forwarded-Proto "https"
    Header always set X-Forwarded-Host "%{HTTP_HOST}s"
</VirtualHost>
```

### HAProxy

```haproxy
frontend galaxy_frontend
    bind *:443 ssl crt /path/to/cert.pem
    default_backend galaxy_backend
    
backend galaxy_backend
    server galaxy1 backend:8000 check
    http-request set-header X-Forwarded-Proto https
    http-request set-header X-Forwarded-Host %[req.hdr(host)]
```

### Traefik

```yaml
# docker-compose.yml
services:
  traefik:
    labels:
      - "traefik.http.routers.galaxy.rule=Host(`galaxy.example.com`)"
      - "traefik.http.routers.galaxy.tls=true"
      - "traefik.http.middlewares.galaxy-headers.headers.customrequestheaders.X-Forwarded-Proto=https"
      - "traefik.http.routers.galaxy.middlewares=galaxy-headers"
```

## Troubleshooting

### Common Issues

**Problem**: Settings not being modified dynamically
```bash
# Configure your shell
export DJANGO_SETTINGS_MODULE=pulpcore.app.settings 
export PULP_SETTINGS=/etc/pulp/settings.py

# Check if hook is enabled
dynaconf inspect -k DYNACONF_AFTER_GET_HOOKS
```

**Problem**: 400 Bad Request in resource server mode
```bash
# Check proxy headers
curl -H "X-Forwarded-Proto: https" -H "Host: galaxy.example.com" \
     https://your-galaxy-instance.com/api/v3/
```

**Problem**: Incorrect protocol detection
```bash
# Verify proxy sends correct headers
# Check proxy logs and configuration
```

### Debug Logging

Enable detailed logging to troubleshoot header processing:

```python
LOGGING = {
    'version': 1,
    'handlers': {
        'console': {
            'class': 'logging.StreamHandler',
        },
    },
    'loggers': {
        'galaxy_ng.app.dynaconf_hooks': {
            'handlers': ['console'],
            'level': 'DEBUG',
        },
    },
}
```

### Testing Headers

Test header processing with curl:

```bash
# Test X-Forwarded headers
curl -H "X-Forwarded-Proto: https" \
     -H "X-Forwarded-Host: api.galaxy.com" \
     https://galaxy.example.com/api/v3/

# Test RFC 7239 Forwarded header  
curl -H "Forwarded: proto=https;host=api.galaxy.com" \
     https://galaxy.example.com/api/v3/
```

## Security Considerations

1. **Header Validation**: Only trusted proxies should set forwarded headers
2. **Resource Server Mode**: Use when headers must be validated strictly  
3. **Proxy Security**: Ensure reverse proxy strips client-provided forwarded headers
4. **SSL Termination**: Use HTTPS between proxy and Galaxy NG when possible

## Migration Notes

The improved `alter_hostname_settings` function is fully backward compatible:

- ✅ Existing deployments continue working without changes
- ✅ New RFC 7239 support is automatically available
- ✅ Resource server validation is opt-in via configuration
- ✅ Script access remains unaffected

No configuration changes are required for existing deployments to benefit from the improvements.

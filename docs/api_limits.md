# API usage limits

Standard API credentials may make up to 120 requests per minute. A response with HTTP status 429 means the limit was exceeded; clients should wait for the Retry-After value before trying again.

The burst limit is 20 requests in any one-second window. Limits apply per API credential, not per end user.

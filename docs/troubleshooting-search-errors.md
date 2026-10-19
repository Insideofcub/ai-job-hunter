# Search error troubleshooting

If Find Jobs shows an error, the UI now formats FastAPI validation errors into readable messages (for example, the exact field and reason), rather than displaying `[object Object]`.

The Find Jobs query supports up to 2,000 characters. For best matching, use a compact title list such as `IT Recruiter, Talent Acquisition Specialist, HR Recruiter`. If you paste a longer instruction, the search parser uses the first sentence to extract role phrases and ignores later instruction sentences for keyword matching.

Source connector failures are shown per source instead of failing the entire search where possible. Check the Source status section beneath results; it distinguishes fetch errors from a successful feed with zero matching fresh jobs.

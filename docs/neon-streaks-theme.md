# Neon Streaks theme (v0.6.0)

The supplied image is copied to `frontend/public/neon-streaks-theme.png` and used locally; it is not fetched from an external host.

The theme updates CSS only. No API, database schema, or application workflow changes are included. The main Overview welcome hero uses the image with a dark left-to-right overlay, and the app background uses a heavier dark overlay to preserve contrast.

To customize the look, edit the v0.6.0 override block at the end of `frontend/src/styles.css`. Keep the local asset filename or update the two `url('/neon-streaks-theme.png')` references accordingly.

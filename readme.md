# Config File

Config file should be placed in `config/config.yaml` (or change the config in the hydra decorator)

The format is:

```
application:
  name: ...
  version: ...
  author:
    username: ...
    reddit_handle: ...
praw:
  client_id: ...
  client_secret: ...
  username: ...
  password: ...
  subreddits:
   - ...
   - ...
```
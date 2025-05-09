# Fire Portfolio Status Discord Bot

A Discord bot that updates the status on your portfolio website's database.

## Setup

1. **Install dependencies**:
   ```
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   - Copy `.env.example` to `.env`
   - Fill in your Discord bot token
   - Add your Neon database URL (same as your portfolio website)
   - Optionally, add allowed Discord user IDs

3. **Create a Discord bot**:
   - Go to [Discord Developer Portal](https://discord.com/developers/applications)
   - Create a new application
   - Go to the "Bot" tab and create a bot
   - Enable "Message Content Intent" under Privileged Gateway Intents
   - Copy the token and add it to your `.env` file
   - Use the OAuth2 URL Generator to invite the bot to your server
     - Select "bot" and "applications.commands" scopes
     - Select appropriate permissions (at minimum: "Send Messages", "Use Slash Commands")

## Running the Bot

```
python bot.py
```

For VPS deployment, you may want to use a process manager like `systemd` or `pm2` to keep the bot running.

## Commands

- `/status` - Check the current status
- `/setstatus <status_type> <message>` - Set a new status
  - `status_type` can be: offline, online, or busy
  - `message` is your custom status message

## Security

- Only users with IDs listed in `ALLOWED_USER_IDS` can change the status
- If `ALLOWED_USER_IDS` is empty, any user can change the status

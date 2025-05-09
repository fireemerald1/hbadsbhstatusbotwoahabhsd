import os
import discord
from discord import app_commands
from discord.ext import commands
import pg8000
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

# Bot configuration
TOKEN = os.getenv('DISCORD_TOKEN')
NEON_DATABASE_URL = os.getenv('NEON_DATABASE_URL')
ALLOWED_USER_IDS = [int(id) for id in os.getenv('ALLOWED_USER_IDS', '').split(',') if id]

# Set up intents
intents = discord.Intents.default()
intents.message_content = True

# Create bot
class StatusBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix='!', intents=intents)
        
    async def setup_hook(self):
        # This will sync the slash commands with Discord
        await self.tree.sync()
        print(f'Synced slash commands for {self.user}')

bot = StatusBot()

# Status types
STATUS_TYPES = ['offline', 'online', 'busy']

@bot.event
async def on_ready():
    print(f'{bot.user} has connected to Discord!')

# Function to connect to database
def get_db_connection():
    try:
        # Parse the connection string
        # Format: postgresql://username:password@host:port/dbname?sslmode=require
        match = re.match(r'postgresql://([^:]+):([^@]+)@([^:/]+)(?::([^/]+))?/([^?]+)', NEON_DATABASE_URL)
        if not match:
            print("Invalid database URL format")
            return None
            
        user, password, host, port, dbname = match.groups()
        port = int(port) if port else 5432
        
        # Connect using pg8000
        conn = pg8000.connect(
            user=user,
            password=password,
            host=host,
            port=port,
            database=dbname,
            ssl_context=True  # Enable SSL
        )
        return conn
    except Exception as e:
        print(f"Database connection error: {e}")
        return None

# Function to update status in database
def update_status_in_db(status_type, status_message):
    conn = get_db_connection()
    if not conn:
        return False, "Failed to connect to database"
    
    try:
        # pg8000 doesn't use cursor objects like psycopg2
        # Check if status exists
        exists = conn.run("SELECT * FROM \"status\" WHERE id = 'current'")
        
        if exists:
            # Update existing status
            conn.run(
                "UPDATE \"status\" SET type = :type, message = :message WHERE id = 'current'",
                type=status_type, message=status_message
            )
        else:
            # Create new status
            conn.run(
                "INSERT INTO \"status\" (id, type, message) VALUES ('current', :type, :message)",
                type=status_type, message=status_message
            )
        
        conn.commit()
        return True, "Status updated successfully"
    except Exception as e:
        return False, f"Error updating status: {e}"
    finally:
        conn.close()

# Function to get current status from database
def get_status_from_db():
    conn = get_db_connection()
    if not conn:
        return None, "Failed to connect to database"
    
    try:
        # pg8000 returns results directly from run method
        result = conn.run("SELECT type, message FROM \"status\" WHERE id = 'current'")
        if result and len(result) > 0:
            return result[0], None  # Return the first row
        else:
            return None, "No status found in database"
    except Exception as e:
        return None, f"Error getting status: {e}"
    finally:
        conn.close()

# Define status choices for the slash command
status_choices = [
    app_commands.Choice(name='Online', value='online'),
    app_commands.Choice(name='Offline', value='offline'),
    app_commands.Choice(name='Busy', value='busy')
]

# Slash command group for status operations
status_group = app_commands.Group(name="status", description="Status commands")

@status_group.command(name="view", description="View current status")
async def status_view(interaction: discord.Interaction):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    status_data, error = get_status_from_db()
    if error:
        await interaction.response.send_message(f"Error: {error}", ephemeral=True)
        return
    
    status_type, status_message = status_data
    embed = discord.Embed(
        title="Current Status",
        description=f"**Type:** {status_type}\n**Message:** {status_message}",
        color=discord.Color.blue()
    )
    await interaction.response.send_message(embed=embed)

@status_group.command(name="set", description="Set your status")
@app_commands.choices(status_type=status_choices)
async def status_set(interaction: discord.Interaction, status_type: app_commands.Choice[str], message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    status_type_value = status_type.value
    status_message = message.strip()
    
    # Update status in database
    success, db_message = update_status_in_db(status_type_value, status_message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** {status_type_value}\n**Message:** {status_message}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="offline", description="Set status to offline with a message")
async def status_offline(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Update status in database
    success, db_message = update_status_in_db("offline", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** offline\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="online", description="Set status to online with a message")
async def status_online(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Update status in database
    success, db_message = update_status_in_db("online", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** online\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="busy", description="Set status to busy with a message")
async def status_busy(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Update status in database
    success, db_message = update_status_in_db("busy", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** busy\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.response.send_message(embed=embed)
    else:
        await interaction.response.send_message(f"Error: {db_message}", ephemeral=True)

# Add the status group to the bot
bot.tree.add_command(status_group)

# Run the bot
if __name__ == "__main__":
    if not TOKEN:
        print("Error: No Discord token provided in .env file")
    else:
        bot.run(TOKEN)

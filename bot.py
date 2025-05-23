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
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    status_data, error = get_status_from_db()
    if error:
        await interaction.followup.send(f"Error: {error}", ephemeral=True)
        return
    
    status_type, status_message = status_data
    embed = discord.Embed(
        title="Current Status",
        description=f"**Type:** {status_type}\n**Message:** {status_message}",
        color=discord.Color.blue()
    )
    await interaction.followup.send(embed=embed)

@status_group.command(name="set", description="Set your status")
@app_commands.choices(status_type=status_choices)
async def status_set(interaction: discord.Interaction, status_type: app_commands.Choice[str], message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
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
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="offline", description="Set status to offline with a message")
async def status_offline(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Update status in database
    success, db_message = update_status_in_db("offline", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** offline\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="online", description="Set status to online with a message")
async def status_online(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Update status in database
    success, db_message = update_status_in_db("online", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** online\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {db_message}", ephemeral=True)

@status_group.command(name="busy", description="Set status to busy with a message")
async def status_busy(interaction: discord.Interaction, message: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Update status in database
    success, db_message = update_status_in_db("busy", message)
    if success:
        embed = discord.Embed(
            title="Status Updated",
            description=f"Your status has been updated to:\n**Type:** busy\n**Message:** {message}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {db_message}", ephemeral=True)

# Database tables are already set up

# Function to add a timeline entry to the database
def add_timeline_entry(date, title, description):
    conn = get_db_connection()
    if not conn:
        return False, "Failed to connect to database"
    
    try:
        # Insert new timeline entry
        conn.run(
            "INSERT INTO \"timeline\" (date, title, description) VALUES (:date, :title, :description)",
            date=date, title=title, description=description
        )
        
        conn.commit()
        return True, "Timeline entry added successfully"
    except Exception as e:
        return False, f"Error adding timeline entry: {e}"
    finally:
        conn.close()

# Function to get timeline entries from database
def get_timeline_entries(limit=10):
    conn = get_db_connection()
    if not conn:
        return None, "Failed to connect to database"
    
    try:
        # Get timeline entries ordered by id (most recent first)
        result = conn.run(f"SELECT id, date, title, description FROM \"timeline\" ORDER BY id DESC LIMIT {limit}")
        return result, None
    except Exception as e:
        return None, f"Error getting timeline entries: {e}"
    finally:
        conn.close()

# Function to edit a timeline entry
def edit_timeline_entry(entry_id, date, title, description):
    conn = get_db_connection()
    if not conn:
        return False, "Failed to connect to database"
    
    try:
        # Check if entry exists
        entry = conn.run("SELECT id FROM \"timeline\" WHERE id = :id", id=entry_id)
        if not entry:
            return False, f"Timeline entry with ID {entry_id} not found"
        
        # Update the entry
        conn.run(
            "UPDATE \"timeline\" SET date = :date, title = :title, description = :description WHERE id = :id",
            id=entry_id, date=date, title=title, description=description
        )
        
        conn.commit()
        return True, "Timeline entry updated successfully"
    except Exception as e:
        return False, f"Error updating timeline entry: {e}"
    finally:
        conn.close()

# Timeline commands group
timeline_group = app_commands.Group(name="timeline", description="Timeline commands")

@timeline_group.command(name="add", description="Add a new timeline entry")
async def timeline_add(interaction: discord.Interaction, date: str, title: str, description: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Add timeline entry to database
    success, message = add_timeline_entry(date, title, description)
    if success:
        embed = discord.Embed(
            title="Timeline Entry Added",
            description=f"**Date:** {date}\n**Title:** {title}\n**Description:** {description}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {message}", ephemeral=True)

@timeline_group.command(name="view", description="View recent timeline entries")
async def timeline_view(interaction: discord.Interaction, limit: int = 5):
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Get timeline entries from database
    entries, error = get_timeline_entries(limit)
    if error and not entries:
        await interaction.followup.send(f"Error: {error}", ephemeral=True)
        return
    
    if not entries:
        await interaction.followup.send("No timeline entries found.")
        return
    
    # Create embed with timeline entries
    embed = discord.Embed(
        title="Timeline Entries",
        description=f"Showing the {len(entries)} most recent timeline entries",
        color=discord.Color.blue()
    )
    
    for entry in entries:
        entry_id, date, title, description = entry
        embed.add_field(
            name=f"ID: {entry_id} | {date} - {title}",
            value=description,
            inline=False
        )
    
    await interaction.followup.send(embed=embed)

@timeline_group.command(name="edit", description="Edit an existing timeline entry")
async def timeline_edit(interaction: discord.Interaction, entry_id: int, date: str, title: str, description: str):
    # Check if user is allowed to use the command
    if ALLOWED_USER_IDS and interaction.user.id not in ALLOWED_USER_IDS:
        await interaction.response.send_message("You are not authorized to use this command.", ephemeral=True)
        return
    
    # Defer the response to prevent timeout
    await interaction.response.defer(ephemeral=False)
    
    # Edit timeline entry in database
    success, message = edit_timeline_entry(entry_id, date, title, description)
    if success:
        embed = discord.Embed(
            title="Timeline Entry Updated",
            description=f"**ID:** {entry_id}\n**Date:** {date}\n**Title:** {title}\n**Description:** {description}",
            color=discord.Color.green()
        )
        await interaction.followup.send(embed=embed)
    else:
        await interaction.followup.send(f"Error: {message}", ephemeral=True)

# Add the command groups to the bot
bot.tree.add_command(status_group)
bot.tree.add_command(timeline_group)

# Run the bot
if __name__ == "__main__":
    if not TOKEN:
        print("Error: No Discord token provided in .env file")
    else:
        bot.run(TOKEN)

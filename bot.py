# Discord bot for artisans directory with interactive buttons only
import discord
from discord.ext import commands

# In-memory stores
artisans: dict[int, dict] = {}
ratings: dict[int, list[int]] = {}
jobs: dict[int, dict] = {}

# ID du canal où le menu principal sera envoyé
HOME_CHANNEL_ID = 123456789012345678  # à modifier

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


class RegisterModal(discord.ui.Modal):
    """Modal d'inscription des artisans."""

    def __init__(self):
        super().__init__(title="Inscription Artisans")
        self.add_item(discord.ui.InputText(label="Métier"))
        self.add_item(discord.ui.InputText(label="Niveau"))
        self.add_item(discord.ui.InputText(label="Prix", placeholder="0 si gratuit"))

    async def callback(self, interaction: discord.Interaction):
        artisans[interaction.user.id] = {
            "nom": interaction.user.display_name,
            "job": self.children[0].value,
            "level": self.children[1].value,
            "price": self.children[2].value,
        }
        await interaction.response.send_message("Inscription enregistrée!", ephemeral=True)


class UpdateModal(discord.ui.Modal):
    """Mise à jour du profil artisan."""

    def __init__(self, artisan_id: int):
        super().__init__(title="Mise à jour Artisans")
        info = artisans.get(artisan_id, {})
        self.add_item(discord.ui.InputText(label="Métier", value=info.get("job", "")))
        self.add_item(discord.ui.InputText(label="Niveau", value=info.get("level", "")))
        self.add_item(discord.ui.InputText(label="Prix", value=info.get("price", "")))

    async def callback(self, interaction: discord.Interaction):
        artisans[interaction.user.id] = {
            "nom": interaction.user.display_name,
            "job": self.children[0].value,
            "level": self.children[1].value,
            "price": self.children[2].value,
        }
        await interaction.response.send_message("Profil mis à jour", ephemeral=True)


class SearchModal(discord.ui.Modal):
    """Recherche d'artisans par métier."""

    def __init__(self):
        super().__init__(title="Recherche Artisans")
        self.add_item(discord.ui.InputText(label="Métier"))

    async def callback(self, interaction: discord.Interaction):
        metier = self.children[0].value
        embed = discord.Embed(title=f"Artisans pour {metier}")
        for uid, info in artisans.items():
            if info["job"].lower() == metier.lower():
                price_display = info["price"] if info["price"] != "0" else "Gratuit"
                embed.add_field(name=info["nom"], value=f"Niveau: {info['level']} | Prix: {price_display}")
        await interaction.response.send_message(embed=embed, ephemeral=True)
        for uid, info in artisans.items():
            if info["job"].lower() == metier.lower():
                await interaction.followup.send(view=artisan_view(uid), ephemeral=True)


class QuoteModal(discord.ui.Modal):
    """Modal pour que l'artisan envoie un devis."""

    def __init__(self, guild_id: int, client_id: int, artisan_id: int):
        super().__init__(title="Envoyer un devis")
        self.guild_id = guild_id
        self.client_id = client_id
        self.artisan_id = artisan_id
        self.add_item(discord.ui.InputText(label="Prix"))
        self.add_item(discord.ui.InputText(label="Détails"))

    async def callback(self, interaction: discord.Interaction):
        price = self.children[0].value
        details = self.children[1].value
        client = bot.get_user(self.client_id)
        if client:
            await client.send(
                f"Devis de {interaction.user.display_name}: {price}\n{details}",
                view=ClientQuoteView(self.guild_id, self.client_id, self.artisan_id),
            )
            await interaction.response.send_message("Devis envoyé au client.", ephemeral=True)
        else:
            await interaction.response.send_message("Client introuvable.", ephemeral=True)


class ClientQuoteView(discord.ui.View):
    """Vue côté client pour accepter ou refuser le devis."""

    def __init__(self, guild_id: int, client_id: int, artisan_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.client_id = client_id
        self.artisan_id = artisan_id

    @discord.ui.button(label="Valider", style=discord.ButtonStyle.success)
    async def validate(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.client_id:
            await interaction.response.send_message("Vous n'êtes pas concerné.", ephemeral=True)
            return
        guild = bot.get_guild(self.guild_id)
        artisan = bot.get_user(self.artisan_id)
        if guild and artisan:
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                artisan: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            for role in guild.roles:
                if role.permissions.administrator:
                    overwrites[role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            channel = await guild.create_text_channel(
                name=f"prestation-{artisan.display_name}", overwrites=overwrites
            )
            jobs[channel.id] = {"artisan_id": self.artisan_id, "client_id": self.client_id}
            await channel.send("Cliquez sur terminer une fois la prestation faite", view=TerminateView(self.artisan_id))
            await interaction.response.send_message(f"Salon créé {channel.mention}", ephemeral=True)
            await artisan.send(f"Votre devis a été accepté. Rendez-vous dans {channel.mention}")
        else:
            await interaction.response.send_message("Erreur lors de la création du salon.", ephemeral=True)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.client_id:
            await interaction.response.send_message("Vous n'êtes pas concerné.", ephemeral=True)
            return
        artisan = bot.get_user(self.artisan_id)
        if artisan:
            await artisan.send("Le client a refusé votre devis.")
        await interaction.response.send_message("Vous avez refusé le devis.", ephemeral=True)


class QuoteView(discord.ui.View):
    """Envoyée à l'artisan pour répondre à une demande."""

    def __init__(self, guild_id: int, client_id: int, artisan_id: int):
        super().__init__()
        self.guild_id = guild_id
        self.client_id = client_id
        self.artisan_id = artisan_id

    @discord.ui.button(label="Envoyer un devis", style=discord.ButtonStyle.success)
    async def send_quote(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(QuoteModal(self.guild_id, self.client_id, self.artisan_id))

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, button: discord.ui.Button, interaction: discord.Interaction):
        client = bot.get_user(self.client_id)
        if client:
            await client.send("Votre demande de devis a été refusée.")
        await interaction.response.send_message("Demande refusée.", ephemeral=True)


class RatingView(discord.ui.View):
    """Vue de notation une fois la prestation terminée."""

    def __init__(self, artisan_id: int):
        super().__init__()
        self.artisan_id = artisan_id

    async def rate(self, interaction: discord.Interaction, value: int):
        ratings.setdefault(self.artisan_id, []).append(value)
        await interaction.response.send_message("Merci pour votre note!", ephemeral=True)
        if interaction.channel and interaction.channel.id in jobs:
            del jobs[interaction.channel.id]
            await interaction.channel.delete()

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary)
    async def rate1(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.rate(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary)
    async def rate2(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.rate(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary)
    async def rate3(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.rate(interaction, 3)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary)
    async def rate4(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.rate(interaction, 4)

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary)
    async def rate5(self, button: discord.ui.Button, interaction: discord.Interaction):
        await self.rate(interaction, 5)


class TerminateView(discord.ui.View):
    """Permet à l'artisan de terminer la prestation."""

    def __init__(self, artisan_id: int):
        super().__init__(timeout=None)
        self.artisan_id = artisan_id

    @discord.ui.button(label="Terminer", style=discord.ButtonStyle.primary)
    async def terminer(self, button: discord.ui.Button, interaction: discord.Interaction):
        if interaction.user.id != self.artisan_id:
            await interaction.response.send_message("Seul l'artisan peut terminer.", ephemeral=True)
            return
        job = jobs.get(interaction.channel.id)
        if not job:
            await interaction.response.send_message("Erreur de prestation.", ephemeral=True)
            return
        client = bot.get_user(job["client_id"])
        if client:
            await interaction.channel.send(f"{client.mention} veuillez noter votre artisan", view=RatingView(self.artisan_id))
            await interaction.response.send_message("Demande de note envoyée.", ephemeral=True)
        else:
            await interaction.response.send_message("Client introuvable.", ephemeral=True)


def artisan_view(artisan_id: int) -> discord.ui.View:
    view = discord.ui.View()

    async def mp_callback(interaction: discord.Interaction):
        user = bot.get_user(artisan_id)
        if user:
            await interaction.response.send_message(f"Contactez {user.mention} en MP.", ephemeral=True)
        else:
            await interaction.response.send_message("Artisan introuvable.", ephemeral=True)

    async def quote_callback(interaction: discord.Interaction):
        artisan = bot.get_user(artisan_id)
        if artisan:
            view_quote = QuoteView(interaction.guild.id, interaction.user.id, artisan_id)
            await artisan.send(
                f"Nouvelle demande de devis de {interaction.user.display_name}",
                view=view_quote,
            )
            await interaction.response.send_message("Demande envoyée!", ephemeral=True)
        else:
            await interaction.response.send_message("Artisan introuvable.", ephemeral=True)

    view.add_item(discord.ui.Button(label="MP", style=discord.ButtonStyle.primary))
    view.add_item(discord.ui.Button(label="Demander un devis", style=discord.ButtonStyle.success))
    view.children[0].callback = mp_callback
    view.children[1].callback = quote_callback
    return view


class MainMenuView(discord.ui.View):
    """Menu principal présenté aux utilisateurs."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Annuaire", style=discord.ButtonStyle.primary)
    async def annuaire(self, button: discord.ui.Button, interaction: discord.Interaction):
        embed = discord.Embed(title="Annuaire des artisans")
        for uid, info in artisans.items():
            note = sum(ratings.get(uid, [])) / len(ratings.get(uid, [1]))
            price_display = info["price"] if info["price"] != "0" else "Gratuit"
            embed.add_field(
                name=info["nom"],
                value=f"Métier: {info['job']} | Niveau: {info['level']} | Prix: {price_display} | Note: {note:.1f}",
            )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        for uid in artisans:
            await interaction.followup.send(view=artisan_view(uid), ephemeral=True)

    @discord.ui.button(label="S'inscrire", style=discord.ButtonStyle.success)
    async def register(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(RegisterModal())

    @discord.ui.button(label="Mise à jour", style=discord.ButtonStyle.secondary)
    async def update(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(UpdateModal(interaction.user.id))

    @discord.ui.button(label="Recherche", style=discord.ButtonStyle.primary)
    async def search(self, button: discord.ui.Button, interaction: discord.Interaction):
        await interaction.response.send_modal(SearchModal())

    @discord.ui.button(label="Top", style=discord.ButtonStyle.primary)
    async def top(self, button: discord.ui.Button, interaction: discord.Interaction):
        sorted_artisans = sorted(artisans.items(), key=lambda a: sum(ratings.get(a[0], [])) / len(ratings.get(a[0], [1])), reverse=True)
        embed = discord.Embed(title="Top Artisans")
        for uid, info in sorted_artisans[:5]:
            note = sum(ratings.get(uid, [])) / len(ratings.get(uid, [1]))
            embed.add_field(name=info["nom"], value=f"Métier: {info['job']} | Note: {note:.1f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Retirer", style=discord.ButtonStyle.danger)
    async def retirer(self, button: discord.ui.Button, interaction: discord.Interaction):
        artisans.pop(interaction.user.id, None)
        ratings.pop(interaction.user.id, None)
        await interaction.response.send_message("Vous avez été retiré de l'annuaire.", ephemeral=True)


@bot.event
async def on_ready():
    channel = bot.get_channel(HOME_CHANNEL_ID)
    if channel:
        await channel.send("Menu Artisans", view=MainMenuView())
    print(f"Logged in as {bot.user}")


bot.run("TOKEN")

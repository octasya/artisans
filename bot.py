# Discord bot for artisans directory with interactive buttons only
import json
import os
import discord
from discord.ext import commands

# In-memory stores
artisans: dict[int, dict] = {}
ratings: dict[int, list[int]] = {}
comments: dict[int, list[str]] = {}
jobs: dict[int, dict] = {}

# Fichier de stockage persistant
DATA_FILE = "data.json"


def load_data():
    """Charge les artisans et notes depuis DATA_FILE."""
    global artisans, ratings, comments
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            artisans = {int(k): v for k, v in data.get("artisans", {}).items()}
            ratings = {int(k): v for k, v in data.get("ratings", {}).items()}
            comments = {int(k): v for k, v in data.get("comments", {}).items()}


def save_data():
    """Sauvegarde les artisans et notes dans DATA_FILE."""
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(
            {"artisans": artisans, "ratings": ratings, "comments": comments}, f
        )

# ID des canaux où les tableaux de bord seront envoyés
ARTISAN_CHANNEL_ID = 123456789012345678  # à modifier
CLIENT_CHANNEL_ID = 987654321098765432  # à modifier

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Charger les données sauvegardées
load_data()


class RegisterModal(discord.ui.Modal):
    """Modal d'inscription des artisans."""

    def __init__(self):
        super().__init__(title="Inscription Artisans")
        self.add_item(
            discord.ui.InputText(
                label="Métiers",
                placeholder="Ex: plombier, électricien",
            )
        )
        self.add_item(discord.ui.InputText(label="Niveau"))
        self.add_item(discord.ui.InputText(label="Prix", placeholder="0 si gratuit"))

    async def callback(self, interaction: discord.Interaction):
        artisans[interaction.user.id] = {
            "nom": interaction.user.display_name,
            "job": self.children[0].value,
            "level": self.children[1].value,
            "price": self.children[2].value,
            "jobs": artisans.get(interaction.user.id, {}).get("jobs", 0),
        }
        save_data()
        await interaction.response.send_message("Inscription enregistrée!", ephemeral=True)


class UpdateModal(discord.ui.Modal):
    """Mise à jour du profil artisan."""

    def __init__(self, artisan_id: int):
        super().__init__(title="Mise à jour Artisans")
        info = artisans.get(artisan_id, {})
        self.add_item(
            discord.ui.InputText(
                label="Métiers",
                value=info.get("job", ""),
                placeholder="plombier, électricien",
            )
        )
        self.add_item(discord.ui.InputText(label="Niveau", value=info.get("level", "")))
        self.add_item(discord.ui.InputText(label="Prix", value=info.get("price", "")))

    async def callback(self, interaction: discord.Interaction):
        previous = artisans.get(interaction.user.id, {})
        artisans[interaction.user.id] = {
            "nom": interaction.user.display_name,
            "job": self.children[0].value,
            "level": self.children[1].value,
            "price": self.children[2].value,
            "jobs": previous.get("jobs", 0),
        }
        save_data()
        await interaction.response.send_message("Profil mis à jour", ephemeral=True)


class SearchModal(discord.ui.Modal):
    """Recherche d'artisans par métier."""

    def __init__(self):
        super().__init__(title="Recherche Artisans")
        self.add_item(discord.ui.InputText(label="Métier"))

    async def callback(self, interaction: discord.Interaction):
        metier = self.children[0].value.lower()
        embed = discord.Embed(title=f"Artisans pour {metier}")
        for uid, info in artisans.items():
            jobs_list = [j.strip().lower() for j in info["job"].split(",")]
            if metier in jobs_list:
                price_display = info["price"] if info["price"] != "0" else "Gratuit"
                embed.add_field(
                    name=info["nom"],
                    value=f"Niveau: {info['level']} | Prix: {price_display}",
                )
        await interaction.response.send_message(embed=embed, ephemeral=True)
        for uid, info in artisans.items():
            jobs_list = [j.strip().lower() for j in info["job"].split(",")]
            if metier in jobs_list:
                await interaction.followup.send(view=artisan_view(uid), ephemeral=True)


class AnnouncementModal(discord.ui.Modal):
    """Modal pour envoyer une annonce à tous les artisans."""

    def __init__(self):
        super().__init__(title="Nouvelle annonce")
        self.add_item(discord.ui.InputText(label="Message"))

    async def callback(self, interaction: discord.Interaction):
        message = self.children[0].value
        for uid in artisans:
            user = bot.get_user(uid)
            if user:
                await user.send(f"Annonce: {message}")
        await interaction.response.send_message("Annonce envoyée", ephemeral=True)


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
    async def validate(self, interaction: discord.Interaction, button: discord.ui.Button):
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
            jobs[channel.id] = {
                "artisan_id": self.artisan_id,
                "client_id": self.client_id,
                "status": "en attente",
            }
            await channel.send(
                "Statut de la prestation : en attente",
                view=JobStatusView(channel.id, self.artisan_id, self.client_id),
            )
            await interaction.response.send_message(f"Salon créé {channel.mention}", ephemeral=True)
            await artisan.send(f"Votre devis a été accepté. Rendez-vous dans {channel.mention}")
        else:
            await interaction.response.send_message("Erreur lors de la création du salon.", ephemeral=True)

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
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
    async def send_quote(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(QuoteModal(self.guild_id, self.client_id, self.artisan_id))

    @discord.ui.button(label="Refuser", style=discord.ButtonStyle.danger)
    async def refuse(self, interaction: discord.Interaction, button: discord.ui.Button):
        client = bot.get_user(self.client_id)
        if client:
            await client.send("Votre demande de devis a été refusée.")
        await interaction.response.send_message("Demande refusée.", ephemeral=True)


class RatingCommentModal(discord.ui.Modal):
    """Modal pour laisser un commentaire avec la note."""

    def __init__(self, artisan_id: int, value: int, channel_id: int | None):
        super().__init__(title="Votre avis")
        self.artisan_id = artisan_id
        self.value = value
        self.channel_id = channel_id
        self.add_item(discord.ui.InputText(label="Commentaire", required=False))

    async def callback(self, interaction: discord.Interaction):
        ratings.setdefault(self.artisan_id, []).append(self.value)
        comments.setdefault(self.artisan_id, []).append(self.children[0].value)
        info = artisans.get(self.artisan_id)
        if info is not None:
            info["jobs"] = info.get("jobs", 0) + 1
        save_data()
        await interaction.response.send_message("Merci pour votre note!", ephemeral=True)
        if self.channel_id and self.channel_id in jobs:
            del jobs[self.channel_id]
            channel = bot.get_channel(self.channel_id)
            if channel:
                await channel.delete()


class RatingView(discord.ui.View):
    """Vue de notation une fois la prestation terminée."""

    def __init__(self, artisan_id: int, channel_id: int | None):
        super().__init__()
        self.artisan_id = artisan_id
        self.channel_id = channel_id

    async def rate(self, interaction: discord.Interaction, value: int):
        await interaction.response.send_modal(
            RatingCommentModal(self.artisan_id, value, self.channel_id)
        )

    @discord.ui.button(label="1", style=discord.ButtonStyle.secondary)
    async def rate1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rate(interaction, 1)

    @discord.ui.button(label="2", style=discord.ButtonStyle.secondary)
    async def rate2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rate(interaction, 2)

    @discord.ui.button(label="3", style=discord.ButtonStyle.secondary)
    async def rate3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rate(interaction, 3)

    @discord.ui.button(label="4", style=discord.ButtonStyle.secondary)
    async def rate4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rate(interaction, 4)

    @discord.ui.button(label="5", style=discord.ButtonStyle.secondary)
    async def rate5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await self.rate(interaction, 5)


class JobStatusView(discord.ui.View):
    """Gère le suivi d'une prestation avec différents statuts."""

    def __init__(self, channel_id: int, artisan_id: int, client_id: int):
        super().__init__(timeout=None)
        self.channel_id = channel_id
        self.artisan_id = artisan_id
        self.client_id = client_id

    @discord.ui.button(label="Démarrer", style=discord.ButtonStyle.primary)
    async def start(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.artisan_id:
            await interaction.response.send_message("Seul l'artisan peut démarrer.", ephemeral=True)
            return
        job = jobs.get(self.channel_id)
        if not job or job.get("status") != "en attente":
            await interaction.response.send_message("Statut invalide.", ephemeral=True)
            return
        job["status"] = "en cours"
        await interaction.channel.send("Statut de la prestation : en cours")
        await interaction.response.send_message("Vous avez démarré la prestation.", ephemeral=True)

    @discord.ui.button(label="Terminer", style=discord.ButtonStyle.success)
    async def terminer(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.artisan_id:
            await interaction.response.send_message("Seul l'artisan peut terminer.", ephemeral=True)
            return
        job = jobs.get(self.channel_id)
        if not job or job.get("status") != "en cours":
            await interaction.response.send_message("La prestation n'est pas en cours.", ephemeral=True)
            return
        job["status"] = "terminé"
        client = bot.get_user(job["client_id"])
        if client:
            await interaction.channel.send(
                f"{client.mention} veuillez noter votre artisan",
                view=RatingView(self.artisan_id, self.channel_id),
            )
            await interaction.response.send_message("Demande de note envoyée.", ephemeral=True)
        else:
            await interaction.response.send_message("Client introuvable.", ephemeral=True)

    @discord.ui.button(label="Appeler un modérateur", style=discord.ButtonStyle.danger)
    async def call_mod(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id not in {self.artisan_id, self.client_id}:
            await interaction.response.send_message(
                "Seuls le client ou l'artisan peuvent appeler un modérateur.", ephemeral=True
            )
            return
        job = jobs.get(self.channel_id)
        if job:
            job["status"] = "litige"
        await interaction.channel.send(
            "Un modérateur a été appelé. Merci de fournir les preuves (captures d'écran du paiement et de la prestation)."
        )
        for role in interaction.guild.roles:
            if role.permissions.administrator:
                await interaction.channel.send(role.mention)
        await interaction.response.send_message("Les modérateurs ont été prévenus.", ephemeral=True)


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
    """Menu général utilisé comme base pour les tableaux de bord."""

    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Annuaire", style=discord.ButtonStyle.primary)
    async def annuaire(self, interaction: discord.Interaction, button: discord.ui.Button):
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
    async def register(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RegisterModal())

    @discord.ui.button(label="Mise à jour", style=discord.ButtonStyle.secondary)
    async def update(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(UpdateModal(interaction.user.id))

    @discord.ui.button(label="Profil", style=discord.ButtonStyle.secondary)
    async def profil(self, interaction: discord.Interaction, button: discord.ui.Button):
        info = artisans.get(interaction.user.id)
        if not info:
            await interaction.response.send_message("Vous n'êtes pas inscrit.", ephemeral=True)
            return
        note_list = ratings.get(interaction.user.id, [])
        note = sum(note_list) / len(note_list) if note_list else 0
        price_display = info["price"] if info["price"] != "0" else "Gratuit"
        embed = discord.Embed(title=f"Profil de {info['nom']}")
        embed.add_field(name="Métier", value=info['job'], inline=True)
        embed.add_field(name="Niveau", value=info['level'], inline=True)
        embed.add_field(name="Prix", value=price_display, inline=True)
        embed.add_field(name="Prestations", value=str(info.get('jobs', 0)), inline=True)
        embed.add_field(name="Note", value=f"{note:.1f}", inline=True)
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Recherche", style=discord.ButtonStyle.primary)
    async def search(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(SearchModal())

    @discord.ui.button(label="Top", style=discord.ButtonStyle.primary)
    async def top(self, interaction: discord.Interaction, button: discord.ui.Button):
        sorted_artisans = sorted(artisans.items(), key=lambda a: sum(ratings.get(a[0], [])) / len(ratings.get(a[0], [1])), reverse=True)
        embed = discord.Embed(title="Top Artisans")
        for uid, info in sorted_artisans[:5]:
            note = sum(ratings.get(uid, [])) / len(ratings.get(uid, [1]))
            embed.add_field(name=info["nom"], value=f"Métier: {info['job']} | Note: {note:.1f}")
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Stats", style=discord.ButtonStyle.primary)
    async def stats(self, interaction: discord.Interaction, button: discord.ui.Button):
        total_artisans = len(artisans)
        total_jobs = sum(info.get("jobs", 0) for info in artisans.values())
        total_ratings = sum(len(ratings.get(uid, [])) for uid in artisans)
        embed = discord.Embed(title="Statistiques")
        embed.add_field(name="Artisans inscrits", value=str(total_artisans))
        embed.add_field(name="Prestations terminées", value=str(total_jobs))
        embed.add_field(name="Notes reçues", value=str(total_ratings))
        await interaction.response.send_message(embed=embed, ephemeral=True)

    @discord.ui.button(label="Annonce", style=discord.ButtonStyle.danger)
    async def annonce(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not any(r.permissions.administrator for r in getattr(interaction.user, "roles", [])):
            await interaction.response.send_message("Permission requise.", ephemeral=True)
            return
        await interaction.response.send_modal(AnnouncementModal())

    @discord.ui.button(label="Retirer", style=discord.ButtonStyle.danger)
    async def retirer(self, interaction: discord.Interaction, button: discord.ui.Button):
        artisans.pop(interaction.user.id, None)
        ratings.pop(interaction.user.id, None)
        save_data()
        await interaction.response.send_message("Vous avez été retiré de l'annuaire.", ephemeral=True)


class ArtisanDashboardView(MainMenuView):
    """Tableau de bord destiné aux artisans."""

    def __init__(self):
        super().__init__()
        # retirer les boutons réservés aux clients
        for label in ["Annuaire", "Recherche", "Top"]:
            for child in list(self.children):
                if isinstance(child, discord.ui.Button) and child.label == label:
                    self.remove_item(child)


class ClientDashboardView(MainMenuView):
    """Tableau de bord destiné aux clients."""

    def __init__(self):
        super().__init__()
        # retirer les boutons réservés aux artisans
        for label in ["S'inscrire", "Mise à jour", "Profil", "Annonce", "Retirer"]:
            for child in list(self.children):
                if isinstance(child, discord.ui.Button) and child.label == label:
                    self.remove_item(child)

@bot.event
async def on_ready():
    artisan_channel = bot.get_channel(ARTISAN_CHANNEL_ID)
    if artisan_channel:
        await artisan_channel.send(
            "Tableau de bord artisans", view=ArtisanDashboardView()
        )
    client_channel = bot.get_channel(CLIENT_CHANNEL_ID)
    if client_channel:
        await client_channel.send(
            "Tableau de bord clients", view=ClientDashboardView()
        )
    print(f"Logged in as {bot.user}")


bot.run("TOKEN")

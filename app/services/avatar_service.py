# -*- coding: utf-8 -*-
"""
Avatar Service - Zentrale Avatar-Aufloesung und Upload-Verarbeitung

Prioritaet: Upload > Shop-PNG > Emoji > Initialen
"""

import os
import json
import logging
from markupsafe import Markup

logger = logging.getLogger(__name__)

USE_POSTGRES = os.getenv('USE_POSTGRES', 'true').lower() == 'true'

try:
    from app.models.cosmetics import UserCosmetic as UserCosmeticModel
    from app.utils.db_utils import db_session_scope
    POSTGRES_AVAILABLE = True
except ImportError:
    POSTGRES_AVAILABLE = False
    USE_POSTGRES = False

# Size presets for avatar HTML rendering
AVATAR_SIZES = {
    'xs': {'css': 'w-6 h-6', 'px': 24, 'font': 'text-xs'},
    'sm': {'css': 'w-8 h-8', 'px': 32, 'font': 'text-sm'},
    'md': {'css': 'w-12 h-12', 'px': 48, 'font': 'text-xl'},
    'lg': {'css': 'w-16 h-16', 'px': 64, 'font': 'text-3xl'},
    'xl': {'css': 'w-24 h-24', 'px': 96, 'font': 'text-5xl'},
    '2xl': {'css': 'w-32 h-32', 'px': 128, 'font': 'text-6xl'},
}

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'webp'}
MAX_FILE_SIZE = 2 * 1024 * 1024  # 2MB
AVATAR_OUTPUT_SIZE = (256, 256)


class AvatarService:
    def __init__(self):
        self.upload_dir = os.path.join('static', 'uploads', 'avatars')
        self.shop_avatars_dir = os.path.join('static', 'avatars')

        # JSON storage for avatar metadata
        persist_base = os.getenv("PERSIST_BASE", "data")
        self.avatars_file = os.path.join(persist_base, "persistent", "user_avatars.json")

        # Ensure directories exist
        os.makedirs(self.upload_dir, exist_ok=True)
        os.makedirs(os.path.dirname(self.avatars_file), exist_ok=True)

        if not os.path.exists(self.avatars_file):
            with open(self.avatars_file, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_avatars(self):
        """Load avatar data — PG-first mit JSON-Fallback"""
        if USE_POSTGRES and POSTGRES_AVAILABLE:
            try:
                with db_session_scope() as session:
                    rows = session.query(UserCosmeticModel).filter(
                        UserCosmeticModel.item_type == 'avatar_custom',
                        UserCosmeticModel.is_active == True
                    ).all()
                    data = {}
                    for row in rows:
                        config = row.config or {}
                        data[row.username] = {
                            "type": config.get("type", "shop"),
                            "path": config.get("url", ""),
                            "updated_at": row.updated_at.isoformat() if hasattr(row, 'updated_at') and row.updated_at else ""
                        }
                    return data
            except Exception as e:
                logger.warning(f"PG avatar read failed: {e}")
        # JSON fallback
        try:
            with open(self.avatars_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _save_avatars(self, data):
        """Save avatar data to JSON"""
        os.makedirs(os.path.dirname(self.avatars_file), exist_ok=True)
        with open(self.avatars_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def _get_active_cosmetics(self, username):
        """Get active cosmetics for a user from cosmetics shop"""
        try:
            from app.services.cosmetics_shop import cosmetics_shop, AVATAR_SHOP
            cosmetics_data = cosmetics_shop.get_user_cosmetics(username)
            active = cosmetics_data.get('active', {})
            return active, AVATAR_SHOP
        except Exception as e:
            logger.debug(f"Could not load cosmetics for {username}: {e}")
            return {}, {}

    def get_avatar_url(self, username):
        """
        Zentrale Avatar-URL-Aufloesung.
        Prioritaet: Upload > Shop-PNG > None (fuer Emoji/Initialen-Fallback)

        Returns:
            str or None: URL zum Avatar-Bild oder None wenn Emoji/Initialen
        """
        if not username:
            return None

        # 1. Check for uploaded avatar
        avatars = self._load_avatars()
        user_data = avatars.get(username, {})

        if user_data.get('type') == 'upload':
            upload_path = user_data.get('path', '')
            if upload_path and os.path.exists(upload_path.lstrip('/')):
                return upload_path

        # 2. Check for shop avatar (PNG image)
        active, avatar_shop = self._get_active_cosmetics(username)
        active_avatar_id = active.get('avatar')

        if active_avatar_id and active_avatar_id in avatar_shop:
            shop_item = avatar_shop[active_avatar_id]
            image_path = shop_item.get('image', '')
            if image_path:
                return image_path

        # 3. Check if avatar data has a stored shop path
        if user_data.get('type') == 'shop' and user_data.get('path'):
            return user_data['path']

        # 4. No image avatar - return None (caller handles emoji/initials)
        return None

    def get_avatar_emoji(self, username):
        """Get the emoji avatar for a user (from cosmetics shop active avatar)"""
        active, avatar_shop = self._get_active_cosmetics(username)
        active_avatar_id = active.get('avatar')

        if active_avatar_id:
            # If it's a shop item, return the emoji
            if active_avatar_id in avatar_shop:
                return avatar_shop[active_avatar_id].get('emoji', '')
            # If it's a raw emoji string (legacy)
            if len(active_avatar_id) <= 4:
                return active_avatar_id

        return None

    def get_avatar_html(self, username, size='md', extra_classes=''):
        """
        Gibt fertiges HTML fuer Avatar-Rendering zurueck.
        Prioritaet: Upload-IMG > Shop-PNG-IMG > Emoji > Initialen

        Args:
            username: Username
            size: 'xs', 'sm', 'md', 'lg', 'xl', '2xl'
            extra_classes: Additional CSS classes

        Returns:
            Markup: Safe HTML string
        """
        size_config = AVATAR_SIZES.get(size, AVATAR_SIZES['md'])
        css_size = size_config['css']
        font_size = size_config['font']

        base_classes = (
            f"{css_size} rounded-full bg-gradient-to-br from-primary to-secondary "
            f"flex items-center justify-center overflow-hidden {extra_classes}"
        ).strip()

        # Try image URL first
        avatar_url = self.get_avatar_url(username)
        if avatar_url:
            return Markup(
                f'<div class="{base_classes}">'
                f'<img src="{avatar_url}" alt="{username}" '
                f'class="w-full h-full object-cover" loading="lazy">'
                f'</div>'
            )

        # Try emoji
        emoji = self.get_avatar_emoji(username)
        if emoji:
            return Markup(
                f'<div class="{base_classes} {font_size}" '
                f'style="line-height: 1;">{emoji}</div>'
            )

        # Fallback: initials
        initial = username[0].upper() if username else '?'
        return Markup(
            f'<div class="{base_classes} {font_size} text-white font-bold" '
            f'style="line-height: 1;">{initial}</div>'
        )

    def save_uploaded_avatar(self, username, file):
        """
        Upload verarbeiten: PNG/JPG/WebP, max 2MB, Resize auf 256x256.
        Speicherung als static/uploads/avatars/{username}.webp

        Args:
            username: Username
            file: werkzeug FileStorage object

        Returns:
            dict: {success, avatar_url, message}
        """
        if not file or not file.filename:
            return {"success": False, "message": "Keine Datei ausgewaehlt"}

        # Check extension
        filename = file.filename.lower()
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        if ext not in ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "message": f"Ungültiges Format. Erlaubt: {', '.join(ALLOWED_EXTENSIONS)}"
            }

        # Check file size (read into memory)
        file_data = file.read()
        if len(file_data) > MAX_FILE_SIZE:
            return {
                "success": False,
                "message": f"Datei zu gross. Maximum: {MAX_FILE_SIZE // (1024*1024)}MB"
            }

        try:
            from PIL import Image
            import io

            # Open and process image
            img = Image.open(io.BytesIO(file_data))

            # Convert to RGB if necessary (for RGBA PNGs)
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if 'A' in img.mode else None)
                img = background
            elif img.mode != 'RGB':
                img = img.convert('RGB')

            # Crop to square (center crop)
            width, height = img.size
            min_dim = min(width, height)
            left = (width - min_dim) // 2
            top = (height - min_dim) // 2
            img = img.crop((left, top, left + min_dim, top + min_dim))

            # Resize to 256x256
            img = img.resize(AVATAR_OUTPUT_SIZE, Image.LANCZOS)

            # Save as WebP
            output_filename = f"{username}.webp"
            output_path = os.path.join(self.upload_dir, output_filename)
            img.save(output_path, 'WEBP', quality=85)

            # URL path for serving
            avatar_url = f"/static/uploads/avatars/{output_filename}"

            # Save to JSON metadata
            avatars = self._load_avatars()
            avatars[username] = {
                "type": "upload",
                "path": avatar_url,
                "original_filename": file.filename,
                "updated_at": self._now_iso()
            }
            self._save_avatars(avatars)

            # Dual-write to PostgreSQL if available
            self._pg_sync_avatar(username, "upload", avatar_url)

            logger.info(f"Avatar uploaded for {username}: {avatar_url}")

            return {
                "success": True,
                "avatar_url": avatar_url,
                "message": "Avatar erfolgreich hochgeladen!"
            }

        except ImportError:
            logger.error("Pillow not installed - cannot process avatar uploads")
            return {"success": False, "message": "Bildverarbeitung nicht verfuegbar"}
        except Exception as e:
            logger.error(f"Avatar upload error for {username}: {e}", exc_info=True)
            return {"success": False, "message": "Fehler beim Verarbeiten des Bildes"}

    def save_shop_avatar(self, username, avatar_id):
        """
        Wenn User einen Shop-Avatar auswaehlt, den Bild-Pfad speichern.

        Args:
            username: Username
            avatar_id: ID des Shop-Avatars (z.B. 'ninja_male')

        Returns:
            dict: {success, avatar_url, message}
        """
        try:
            from app.services.cosmetics_shop import AVATAR_SHOP

            if avatar_id not in AVATAR_SHOP:
                return {"success": False, "message": "Avatar nicht gefunden"}

            shop_item = AVATAR_SHOP[avatar_id]
            image_path = shop_item.get('image', '')

            # Save to JSON metadata
            avatars = self._load_avatars()
            avatars[username] = {
                "type": "shop",
                "avatar_id": avatar_id,
                "path": image_path,
                "updated_at": self._now_iso()
            }
            self._save_avatars(avatars)

            # Dual-write to PostgreSQL
            self._pg_sync_avatar(username, "shop", image_path)

            logger.info(f"Shop avatar set for {username}: {avatar_id}")

            return {
                "success": True,
                "avatar_url": image_path,
                "message": f"Avatar '{shop_item['name']}' ausgewaehlt!"
            }

        except Exception as e:
            logger.error(f"Shop avatar error for {username}: {e}", exc_info=True)
            return {"success": False, "message": "Fehler beim Setzen des Avatars"}

    def delete_avatar(self, username):
        """
        Avatar loeschen - zurueck zu Emoji/Initialen.

        Returns:
            dict: {success, message}
        """
        try:
            avatars = self._load_avatars()
            user_data = avatars.get(username, {})

            # Delete uploaded file if exists
            if user_data.get('type') == 'upload' and user_data.get('path'):
                file_path = user_data['path'].lstrip('/')
                if os.path.exists(file_path):
                    os.remove(file_path)
                    logger.info(f"Deleted avatar file for {username}: {file_path}")

            # Remove from JSON
            if username in avatars:
                del avatars[username]
                self._save_avatars(avatars)

            # Dual-write to PostgreSQL
            self._pg_sync_avatar(username, None, None)

            logger.info(f"Avatar deleted for {username}")

            return {"success": True, "message": "Avatar entfernt"}

        except Exception as e:
            logger.error(f"Avatar delete error for {username}: {e}", exc_info=True)
            return {"success": False, "message": "Fehler beim Entfernen des Avatars"}

    def get_avatar_data(self, username):
        """Get raw avatar data for a user"""
        avatars = self._load_avatars()
        return avatars.get(username, {})

    def get_all_avatar_urls(self, usernames):
        """
        Batch-Aufloesung fuer Scoreboard etc.

        Args:
            usernames: Liste von Usernames

        Returns:
            dict: {username: avatar_url_or_None}
        """
        result = {}
        for username in usernames:
            result[username] = self.get_avatar_url(username)
        return result

    def _now_iso(self):
        """Current timestamp as ISO string"""
        from datetime import datetime
        import pytz
        tz = pytz.timezone("Europe/Berlin")
        return datetime.now(tz).isoformat()

    def _pg_sync_avatar(self, username, avatar_type, avatar_url):
        """Dual-Write: Avatar-Daten in PostgreSQL syncen"""
        try:
            from app.models.cosmetics import UserCosmetic
            from app.core.extensions import db

            existing = UserCosmetic.query.filter_by(
                username=username, item_type='avatar_custom'
            ).first()

            if avatar_type is None:
                # Delete
                if existing:
                    db.session.delete(existing)
                    db.session.commit()
                return

            if existing:
                existing.config = {"type": avatar_type, "url": avatar_url}
                existing.is_active = True
            else:
                from datetime import datetime
                import pytz
                tz = pytz.timezone("Europe/Berlin")
                cosmetic = UserCosmetic(
                    username=username,
                    item_id=f"avatar_custom_{username}",
                    item_type="avatar_custom",
                    item_category="visual",
                    name="Custom Avatar",
                    description=f"Custom avatar for {username}",
                    rarity="common",
                    is_owned=True,
                    is_active=True,
                    unlock_date=datetime.now(tz),
                    config={"type": avatar_type, "url": avatar_url},
                )
                db.session.add(cosmetic)

            db.session.commit()
        except Exception as e:
            logger.debug(f"PG avatar sync skipped: {e}")


# Global instance
avatar_service = AvatarService()

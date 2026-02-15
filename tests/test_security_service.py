# -*- coding: utf-8 -*-
"""
Tests for Security Service
"""

import pytest
import pyotp
from unittest.mock import patch, MagicMock


class TestSecurityServicePassword:
    """Tests for password functionality"""

    @pytest.fixture
    def security_service(self, mock_data_persistence):
        """Create SecurityService with mocked data persistence"""
        from app.services.security_service import SecurityService

        service = SecurityService()

        # Patch the data persistence calls
        with patch.object(service, '_load_passwords', return_value={}):
            with patch.object(service, '_save_passwords'):
                yield service

    @pytest.fixture
    def security_service_with_data(self, mock_data_persistence):
        """Create SecurityService with actual temp data persistence"""
        from app.services.security_service import SecurityService

        # Patch data_persistence to use mock
        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()
            yield service, mock_data_persistence

    @pytest.mark.unit
    def test_hash_password_returns_bcrypt_hash(self):
        """Test that password hashing returns bcrypt format"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        hashed = service.hash_password('test123')

        assert hashed.startswith('$2b$')
        assert len(hashed) == 60  # bcrypt hash length

    @pytest.mark.unit
    def test_hash_password_different_each_time(self):
        """Test that same password produces different hashes (salt)"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        hash1 = service.hash_password('test123')
        hash2 = service.hash_password('test123')

        assert hash1 != hash2  # Different salts

    @pytest.mark.unit
    def test_verify_hashed_password_correct(self):
        """Test password verification with correct password"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        hashed = service.hash_password('test123')
        result = service.verify_hashed_password('test123', hashed)

        assert result is True

    @pytest.mark.unit
    def test_verify_hashed_password_incorrect(self):
        """Test password verification with incorrect password"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        hashed = service.hash_password('test123')
        result = service.verify_hashed_password('wrong', hashed)

        assert result is False

    @pytest.mark.unit
    def test_verify_hashed_password_invalid_hash(self):
        """Test password verification with invalid hash"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        result = service.verify_hashed_password('test123', 'not-a-valid-hash')

        assert result is False

    @pytest.mark.unit
    def test_is_hashed_password_bcrypt(self):
        """Test detection of bcrypt hashes"""
        from app.services.security_service import SecurityService

        service = SecurityService()
        hashed = service.hash_password('test123')

        assert service.is_hashed_password(hashed) is True

    @pytest.mark.unit
    def test_is_hashed_password_plaintext(self):
        """Test detection of plaintext passwords"""
        from app.services.security_service import SecurityService

        service = SecurityService()

        assert service.is_hashed_password('plaintext') is False
        assert service.is_hashed_password('') is False

    @pytest.mark.unit
    def test_verify_password_with_custom_hashed(self, mock_data_persistence):
        """Test password verification with custom hashed password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Save a hashed password
            hashed = service.hash_password('secure123')
            mock_data_persistence.save_data('user_passwords', {'test_user': hashed})

            result = service.verify_password('test_user', 'secure123')

            assert result is True

    @pytest.mark.unit
    def test_verify_password_rejects_plaintext(self, mock_data_persistence):
        """Test that plaintext passwords in custom_passwords are rejected (no fallback)"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Save a plaintext password (legacy — should be blocked)
            mock_data_persistence.save_data('user_passwords', {'test_user': 'plaintext123'})

            result = service.verify_password('test_user', 'plaintext123')

            assert result is False

    @pytest.mark.unit
    def test_verify_password_rejects_userlist_without_hash(self, mock_data_persistence):
        """Test that USERLIST users without hashed custom_passwords are rejected"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist') as mock_userlist:
                mock_userlist.return_value = {'env_user': 'env_password'}

                service = SecurityService()
                result = service.verify_password('env_user', 'env_password')

                # Should be rejected — migration should have pre-hashed this
                assert result is False

    @pytest.mark.unit
    def test_verify_password_nonexistent_user(self, mock_data_persistence):
        """Test password verification for non-existent user"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist', return_value={}):
                service = SecurityService()
                result = service.verify_password('nonexistent', 'password')

                assert result is False

    @pytest.mark.unit
    def test_change_password_success(self, mock_data_persistence):
        """Test successful password change"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist') as mock_userlist:
                mock_userlist.return_value = {}

                service = SecurityService()

                # Pre-hash old password (simulates migrated state)
                hashed_old = service.hash_password('old_password')
                mock_data_persistence.save_data('user_passwords', {'test_user': hashed_old})

                success, message = service.change_password(
                    'test_user', 'old_password', 'new_secure_password'
                )

                assert success is True
                assert 'erfolgreich' in message

                # Verify new password works
                assert service.verify_password('test_user', 'new_secure_password') is True

    @pytest.mark.unit
    def test_change_password_wrong_old_password(self, mock_data_persistence):
        """Test password change with wrong old password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist') as mock_userlist:
                mock_userlist.return_value = {'test_user': 'correct_password'}

                service = SecurityService()
                success, message = service.change_password(
                    'test_user', 'wrong_password', 'new_password'
                )

                assert success is False
                assert 'falsch' in message

    @pytest.mark.unit
    def test_change_password_too_short(self, mock_data_persistence):
        """Test password change with too short new password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()
            success, message = service.change_password(
                'test_user', 'old_password', 'short'
            )

            assert success is False
            assert '6 Zeichen' in message

    @pytest.mark.unit
    def test_change_password_too_long(self, mock_data_persistence):
        """Test password change with too long new password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()
            success, message = service.change_password(
                'test_user', 'old_password', 'x' * 101
            )

            assert success is False
            assert '100' in message


class TestSecurityService2FA:
    """Tests for 2FA functionality"""

    @pytest.mark.unit
    def test_setup_2fa_returns_valid_data(self, mock_data_persistence):
        """Test that 2FA setup returns valid secret and QR code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()
            secret, qr_base64, backup_codes = service.setup_2fa('test_user')

            # Secret should be valid base32
            assert len(secret) == 32  # pyotp default length
            assert secret.isalnum()

            # QR code should be base64 encoded
            assert len(qr_base64) > 0

            # Should have 10 backup codes
            assert len(backup_codes) == 10

    @pytest.mark.unit
    def test_setup_2fa_generates_unique_codes(self, mock_data_persistence):
        """Test that backup codes are unique"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()
            _, _, backup_codes = service.setup_2fa('test_user')

            # All codes should be unique
            assert len(set(backup_codes)) == len(backup_codes)

    @pytest.mark.unit
    def test_enable_2fa_with_valid_code(self, mock_data_persistence):
        """Test enabling 2FA with valid verification code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup 2FA
            secret, _, _ = service.setup_2fa('test_user')

            # Generate valid TOTP code
            totp = pyotp.TOTP(secret)
            valid_code = totp.now()

            # Enable 2FA
            success, message = service.enable_2fa('test_user', valid_code)

            assert success is True
            assert 'aktiviert' in message

    @pytest.mark.unit
    def test_enable_2fa_with_invalid_code(self, mock_data_persistence):
        """Test enabling 2FA with invalid verification code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup 2FA
            service.setup_2fa('test_user')

            # Try to enable with wrong code
            success, message = service.enable_2fa('test_user', '000000')

            assert success is False
            assert 'Ungültig' in message

    @pytest.mark.unit
    def test_enable_2fa_without_setup(self, mock_data_persistence):
        """Test enabling 2FA without prior setup"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            success, message = service.enable_2fa('test_user', '123456')

            assert success is False
            assert 'nicht eingerichtet' in message

    @pytest.mark.unit
    def test_verify_2fa_with_totp_code(self, mock_data_persistence):
        """Test 2FA verification with valid TOTP code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup and enable 2FA
            secret, _, _ = service.setup_2fa('test_user')
            totp = pyotp.TOTP(secret)
            service.enable_2fa('test_user', totp.now())

            # Verify with TOTP
            result = service.verify_2fa('test_user', totp.now())

            assert result is True

    @pytest.mark.unit
    def test_verify_2fa_with_backup_code(self, mock_data_persistence):
        """Test 2FA verification with backup code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup and enable 2FA
            secret, _, backup_codes = service.setup_2fa('test_user')
            totp = pyotp.TOTP(secret)
            service.enable_2fa('test_user', totp.now())

            # Verify with backup code
            result = service.verify_2fa('test_user', backup_codes[0])

            assert result is True

    @pytest.mark.unit
    def test_verify_2fa_backup_code_single_use(self, mock_data_persistence):
        """Test that backup codes can only be used once"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup and enable 2FA
            secret, _, backup_codes = service.setup_2fa('test_user')
            totp = pyotp.TOTP(secret)
            service.enable_2fa('test_user', totp.now())

            # First use should succeed
            assert service.verify_2fa('test_user', backup_codes[0]) is True

            # Second use should fail
            assert service.verify_2fa('test_user', backup_codes[0]) is False

    @pytest.mark.unit
    def test_verify_2fa_when_not_enabled(self, mock_data_persistence):
        """Test that 2FA verification passes when not enabled"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # No 2FA setup
            result = service.verify_2fa('test_user', 'any_code')

            assert result is True

    @pytest.mark.unit
    def test_verify_2fa_with_wrong_code(self, mock_data_persistence):
        """Test 2FA verification with wrong code"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup and enable 2FA
            secret, _, _ = service.setup_2fa('test_user')
            totp = pyotp.TOTP(secret)
            service.enable_2fa('test_user', totp.now())

            # Verify with wrong code
            result = service.verify_2fa('test_user', '000000')

            assert result is False

    @pytest.mark.unit
    def test_disable_2fa_success(self, mock_data_persistence):
        """Test disabling 2FA with correct password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist') as mock_userlist:
                mock_userlist.return_value = {}

                service = SecurityService()

                # Pre-hash password (simulates migrated state)
                hashed_pw = service.hash_password('password123')
                mock_data_persistence.save_data('user_passwords', {'test_user': hashed_pw})

                # Setup and enable 2FA
                secret, _, _ = service.setup_2fa('test_user')
                totp = pyotp.TOTP(secret)
                service.enable_2fa('test_user', totp.now())

                # Disable 2FA
                success, message = service.disable_2fa('test_user', 'password123')

                assert success is True
                assert 'deaktiviert' in message

                # 2FA should no longer be enabled
                assert service.is_2fa_enabled('test_user') is False

    @pytest.mark.unit
    def test_disable_2fa_wrong_password(self, mock_data_persistence):
        """Test disabling 2FA with wrong password"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            with patch('app.services.security_service.get_userlist') as mock_userlist:
                mock_userlist.return_value = {'test_user': 'password123'}

                service = SecurityService()

                # Setup and enable 2FA
                secret, _, _ = service.setup_2fa('test_user')
                totp = pyotp.TOTP(secret)
                service.enable_2fa('test_user', totp.now())

                # Try to disable with wrong password
                success, message = service.disable_2fa('test_user', 'wrong_password')

                assert success is False
                assert 'falsch' in message

    @pytest.mark.unit
    def test_is_2fa_enabled_true(self, mock_data_persistence):
        """Test checking if 2FA is enabled"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup and enable 2FA
            secret, _, _ = service.setup_2fa('test_user')
            totp = pyotp.TOTP(secret)
            service.enable_2fa('test_user', totp.now())

            assert service.is_2fa_enabled('test_user') is True

    @pytest.mark.unit
    def test_is_2fa_enabled_false(self, mock_data_persistence):
        """Test checking if 2FA is disabled"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            assert service.is_2fa_enabled('test_user') is False

    @pytest.mark.unit
    def test_get_backup_codes_returns_list(self, mock_data_persistence):
        """Test getting backup codes"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            # Setup 2FA
            service.setup_2fa('test_user')

            codes = service.get_backup_codes('test_user')

            assert isinstance(codes, list)
            assert len(codes) == 10

    @pytest.mark.unit
    def test_get_backup_codes_empty_for_nonexistent(self, mock_data_persistence):
        """Test getting backup codes for user without 2FA"""
        from app.services.security_service import SecurityService

        with patch('app.services.security_service.data_persistence', mock_data_persistence):
            service = SecurityService()

            codes = service.get_backup_codes('nonexistent_user')

            assert codes == []

"""Offline tests for the DNS NOC bot's Telegram access controls and config."""
import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import bot


class ConfigTests(unittest.TestCase):
    def test_parse_id_list(self):
        with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USER_IDS": "123, 456,123"}):
            self.assertEqual(bot.parse_allowed_ids("TELEGRAM_ALLOWED_USER_IDS"), {123, 456})

    def test_parse_group_chat_id(self):
        with patch.dict(os.environ, {"TELEGRAM_ALLOWED_CHAT_IDS": "-100123456789, 123"}):
            self.assertEqual(bot.parse_allowed_ids("TELEGRAM_ALLOWED_CHAT_IDS"), {-100123456789, 123})

    def test_invalid_id_rejected(self):
        with patch.dict(os.environ, {"TELEGRAM_ALLOWED_USER_IDS": "admin"}):
            with self.assertRaises(RuntimeError):
                bot.parse_allowed_ids("TELEGRAM_ALLOWED_USER_IDS")

    def test_no_permission_lists_fail_closed(self):
        with patch.multiple(
            bot,
            BOT_TOKEN="token",
            PROM_URL="http://localhost:9090",
            HOST_MAP={"dns1": "dns1:9100", "dns2": "dns2:9100"},
            CONNTRACK_NODE="hypervisor:9100",
            ALLOWED_USER_IDS=set(),
            ALLOWED_CHAT_IDS=set(),
        ):
            with self.assertRaisesRegex(RuntimeError, "TELEGRAM_ALLOWED_USER_IDS"):
                bot.validate_configuration()

    def test_required_configuration_passes(self):
        with patch.multiple(
            bot,
            BOT_TOKEN="token",
            PROM_URL="http://localhost:9090",
            HOST_MAP={"dns1": "dns1:9100", "dns2": "dns2:9100"},
            CONNTRACK_NODE="hypervisor:9100",
            ALLOWED_USER_IDS={123},
            ALLOWED_CHAT_IDS={123},
        ):
            bot.validate_configuration()

    def test_dns_hosts_exclude_hypervisor(self):
        self.assertEqual(set(bot.HOST_MAP), {"dns1", "dns2"})


class AuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def test_allowed_user_in_allowed_chat_can_run(self):
        called = []
        async def command(update, context):
            called.append(True)
            return "ok"
        msg = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=7),
            effective_chat=SimpleNamespace(id=-1009),
            effective_message=msg,
        )
        with patch.object(bot, "ALLOWED_USER_IDS", {7}), patch.object(bot, "ALLOWED_CHAT_IDS", {-1009}):
            outcome = await bot.require_authorization(command)(update, object())
        self.assertEqual(outcome, "ok")
        self.assertEqual(called, [True])
        msg.reply_text.assert_not_awaited()

    async def test_unknown_user_cannot_run(self):
        command = AsyncMock()
        msg = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=99),
            effective_chat=SimpleNamespace(id=-1009),
            effective_message=msg,
        )
        with patch.object(bot, "ALLOWED_USER_IDS", {7}), patch.object(bot, "ALLOWED_CHAT_IDS", {-1009}):
            await bot.require_authorization(command)(update, object())
        command.assert_not_awaited()
        msg.reply_text.assert_awaited_once_with("Access denied")

    async def test_correct_user_in_wrong_chat_cannot_run(self):
        command = AsyncMock()
        msg = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_user=SimpleNamespace(id=7),
            effective_chat=SimpleNamespace(id=-1010),
            effective_message=msg,
        )
        with patch.object(bot, "ALLOWED_USER_IDS", {7}), patch.object(bot, "ALLOWED_CHAT_IDS", {-1009}):
            await bot.require_authorization(command)(update, object())
        command.assert_not_awaited()
        msg.reply_text.assert_awaited_once_with("Access denied")


if __name__ == "__main__":
    unittest.main()

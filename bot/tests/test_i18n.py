"""T-047c: bot yanıt dili (ja/tr/en)."""
import i18n


def test_default_is_japanese(bot):
    msg, _ = bot.respond("u-ja", "合計")
    assert msg.startswith("今月の集計")


def test_language_prompt_and_set(bot):
    msg, options = bot.respond("u-tr", "dil")
    assert [s for _, s in options] == ["言語:ja", "言語:tr", "言語:en"]
    msg, options = bot.respond("u-tr", "言語:tr")
    assert "Dil Türkçe olarak ayarlandı." in msg
    assert "「Toplam」" in msg
    assert ("Toplam", "Toplam") in options


def test_turkish_flow(bot):
    bot.respond("u-tr2", "Türkçe")
    msg, options = bot.respond("u-tr2", "タクシー 2300")
    assert msg.startswith("Kaydedildi ✅")
    assert "タクシー  ¥2,300" in msg            # veri çevrilmez
    assert "旅費交通費" in msg                  # 勘定科目 Japonca kalır
    assert "「Geri al」" in msg
    labels = [l for l, _ in options]
    assert "Geri al" in labels and "📷 Fiş" in labels
    camera = [s for l, s in options if l == "📷 Fiş"][0]
    assert camera == "📷 レシート"              # LINE kamera düğmesi bozulmaz
    msg, _ = bot.respond("u-tr2", "Toplam")
    assert msg.startswith("Bu ayın özeti") and "Gider ¥2,300" in msg
    msg, _ = bot.respond("u-tr2", "Geri al")
    assert "geri alındı" in msg


def test_english_flow(bot):
    bot.respond("u-en", "language: english")
    msg, _ = bot.respond("u-en", "Total")
    assert msg.startswith("This month")
    msg, _ = bot.respond("u-en", "help")
    assert "Send a receipt photo" in msg


def test_back_to_japanese(bot):
    bot.respond("u-x", "English")
    bot.respond("u-x", "日本語")
    msg, _ = bot.respond("u-x", "合計")
    assert msg.startswith("今月の集計")


def test_unknown_language_shows_prompt(bot):
    msg, options = bot.respond("u-y", "dil: klingon")
    assert len(options) == 3


def test_text_without_translation_falls_back():
    assert i18n.text("tr", "未知のメッセージ") == "未知のメッセージ"
    assert i18n.text("ja", i18n.HELP_JA) == i18n.HELP_JA
    assert "Fiş fotoğrafı" in i18n.text("tr", i18n.HELP_JA)

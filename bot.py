"""
🏋️ בוט טלגרם למעקב תזונה וכושר
"""

import json
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, 
    CommandHandler, 
    MessageHandler, 
    CallbackQueryHandler,
    ConversationHandler,
    ContextTypes,
    filters
)

BOT_TOKEN = os.environ.get("BOT_TOKEN")

WAITING_MEAL_NAME, WAITING_MEAL_CALORIES, WAITING_MEAL_PROTEIN = range(3)
WAITING_WORKOUT_TYPE, WAITING_WORKOUT_DURATION = range(10, 12)
WAITING_WEIGHT = 20

DATA_FILE = "fitness_data.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def save_data(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user_data(user_id):
    data = load_data()
    user_id = str(user_id)
    if user_id not in data:
        data[user_id] = {
            "meals": [],
            "workouts": [],
            "weights": [],
            "settings": {"target_calories": 2000, "target_protein": 150}
        }
        save_data(data)
    return data[user_id]

def save_user_data(user_id, user_data):
    data = load_data()
    data[str(user_id)] = user_data
    save_data(data)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        ["🍽️ הוסף ארוחה", "💪 הוסף אימון"],
        ["⚖️ עדכן משקל", "📊 סיכום יומי"],
        ["📈 סיכום שבועי", "⚙️ הגדרות"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    
    await update.message.reply_text(
        "🏋️ *ברוך הבא לבוט מעקב תזונה וכושר!*\n\n"
        "אני אעזור לך לעקוב אחרי:\n"
        "• 🍽️ ארוחות וקלוריות\n"
        "• 💪 אימונים\n"
        "• ⚖️ משקל\n\n"
        "בחר אפשרות מהתפריט!",
        reply_markup=reply_markup,
        parse_mode='Markdown'
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 *פקודות:*\n\n"
        "/meal - הוסף ארוחה\n"
        "/workout - הוסף אימון\n"
        "/weight - עדכן משקל\n"
        "/today - סיכום יומי\n"
        "/week - סיכום שבועי\n\n"
        "*קיצורים:*\n"
        "`ארוחה: שם, קלוריות, חלבון`\n"
        "`אימון: סוג, דקות`\n"
        "`משקל: 75.5`",
        parse_mode='Markdown'
    )

async def add_meal_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("☕ בוקר - 350 קל'", callback_data="quick_meal_בוקר_350_15")],
        [InlineKeyboardButton("🥗 סלט עוף - 450 קל'", callback_data="quick_meal_סלט עוף_450_40")],
        [InlineKeyboardButton("🥤 שייק חלבון - 250 קל'", callback_data="quick_meal_שייק חלבון_250_30")],
        [InlineKeyboardButton("🥪 סנדוויץ' - 400 קל'", callback_data="quick_meal_סנדוויץ'_400_20")],
        [InlineKeyboardButton("🍝 צהריים - 600 קל'", callback_data="quick_meal_צהריים_600_35")],
        [InlineKeyboardButton("🍽️ ערב - 500 קל'", callback_data="quick_meal_ערב_500_30")],
        [InlineKeyboardButton("✏️ הזנה ידנית", callback_data="manual_meal")]
    ]
    await update.message.reply_text(
        "🍽️ *הוספת ארוחה*\n\nבחר או הזן ידנית:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return WAITING_MEAL_NAME

async def quick_meal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "manual_meal":
        await query.edit_message_text("✏️ הקלד את שם הארוחה:")
        return WAITING_MEAL_NAME
    
    parts = query.data.replace("quick_meal_", "").split("_")
    name, calories, protein = parts[0], int(parts[1]), int(parts[2])
    
    user_data = get_user_data(query.from_user.id)
    user_data["meals"].append({
        "name": name, "calories": calories, "protein": protein,
        "date": datetime.now().isoformat()
    })
    save_user_data(query.from_user.id, user_data)
    
    today = datetime.now().date()
    today_meals = [m for m in user_data["meals"] if datetime.fromisoformat(m["date"]).date() == today]
    total_cal = sum(m["calories"] for m in today_meals)
    target = user_data["settings"]["target_calories"]
    
    await query.edit_message_text(
        f"✅ *נרשם: {name}*\n🔥 {calories} קל' | 💪 {protein}g\n\n"
        f"📊 היום: {total_cal}/{target} קל' ({int(total_cal/target*100)}%)",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def meal_name_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['meal_name'] = update.message.text
    await update.message.reply_text("🔥 כמה קלוריות?")
    return WAITING_MEAL_CALORIES

async def meal_calories_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        context.user_data['meal_calories'] = int(update.message.text)
        await update.message.reply_text("💪 כמה גרם חלבון? (או 0)")
        return WAITING_MEAL_PROTEIN
    except ValueError:
        await update.message.reply_text("❌ מספר בלבד")
        return WAITING_MEAL_CALORIES

async def meal_protein_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        protein = int(update.message.text)
    except:
        protein = 0
    
    user_data = get_user_data(update.effective_user.id)
    meal = {
        "name": context.user_data['meal_name'],
        "calories": context.user_data['meal_calories'],
        "protein": protein,
        "date": datetime.now().isoformat()
    }
    user_data["meals"].append(meal)
    save_user_data(update.effective_user.id, user_data)
    
    today = datetime.now().date()
    today_meals = [m for m in user_data["meals"] if datetime.fromisoformat(m["date"]).date() == today]
    total_cal = sum(m["calories"] for m in today_meals)
    target = user_data["settings"]["target_calories"]
    
    await update.message.reply_text(
        f"✅ *נרשם: {meal['name']}*\n🔥 {meal['calories']} קל' | 💪 {protein}g\n\n"
        f"📊 היום: {total_cal}/{target} קל'",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def add_workout_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🏃 ריצה", callback_data="workout_ריצה"),
         InlineKeyboardButton("🚶 הליכה", callback_data="workout_הליכה")],
        [InlineKeyboardButton("🏋️ חדר כושר", callback_data="workout_חדר כושר"),
         InlineKeyboardButton("🚴 אופניים", callback_data="workout_אופניים")],
        [InlineKeyboardButton("🏀 כדורסל", callback_data="workout_כדורסל"),
         InlineKeyboardButton("⚽ כדורגל", callback_data="workout_כדורגל")],
        [InlineKeyboardButton("🏊 שחייה", callback_data="workout_שחייה"),
         InlineKeyboardButton("🧘 יוגה", callback_data="workout_יוגה")],
        [InlineKeyboardButton("✏️ אחר", callback_data="workout_custom")]
    ]
    await update.message.reply_text(
        "💪 *הוספת אימון*\n\nבחר סוג:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )
    return WAITING_WORKOUT_TYPE

async def workout_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    workout_type = query.data.replace("workout_", "")
    
    if workout_type == "custom":
        await query.edit_message_text("✏️ הקלד סוג אימון:")
        return WAITING_WORKOUT_TYPE
    
    context.user_data['workout_type'] = workout_type
    await query.edit_message_text(f"⏱️ כמה דקות {workout_type}?")
    return WAITING_WORKOUT_DURATION

async def workout_type_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['workout_type'] = update.message.text
    await update.message.reply_text("⏱️ כמה דקות?")
    return WAITING_WORKOUT_DURATION

async def workout_duration_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        duration = int(update.message.text)
    except:
        await update.message.reply_text("❌ מספר בלבד")
        return WAITING_WORKOUT_DURATION
    
    user_data = get_user_data(update.effective_user.id)
    user_data["workouts"].append({
        "type": context.user_data['workout_type'],
        "duration": duration,
        "date": datetime.now().isoformat()
    })
    save_user_data(update.effective_user.id, user_data)
    
    week_ago = datetime.now() - timedelta(days=7)
    week_workouts = [w for w in user_data["workouts"] if datetime.fromisoformat(w["date"]) > week_ago]
    total_minutes = sum(w["duration"] for w in week_workouts)
    
    await update.message.reply_text(
        f"✅ *נרשם: {context.user_data['workout_type']}*\n⏱️ {duration} דקות\n\n"
        f"📊 השבוע: {total_minutes} דקות",
        parse_mode='Markdown'
    )
    return ConversationHandler.END

async def add_weight_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    last = ""
    if user_data["weights"]:
        w = user_data["weights"][-1]
        last = f"\n📌 אחרון: {w['value']} ק\"ג"
    
    await update.message.reply_text(f"⚖️ *עדכון משקל*{last}\n\nהקלד משקל:", parse_mode='Markdown')
    return WAITING_WEIGHT

async def weight_received(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        weight = float(update.message.text.replace(",", "."))
    except:
        await update.message.reply_text("❌ מספר בלבד (לדוגמה: 75.5)")
        return WAITING_WEIGHT
    
    user_data = get_user_data(update.effective_user.id)
    user_data["weights"].append({"value": weight, "date": datetime.now().isoformat()})
    save_user_data(update.effective_user.id, user_data)
    
    change = ""
    if len(user_data["weights"]) > 1:
        diff = weight - user_data["weights"][-2]["value"]
        emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        change = f"\n{emoji} שינוי: {diff:+.1f} ק\"ג"
    
    await update.message.reply_text(f"✅ *משקל: {weight} ק\"ג*{change}", parse_mode='Markdown')
    return ConversationHandler.END

async def today_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    today = datetime.now().date()
    
    today_meals = [m for m in user_data["meals"] if datetime.fromisoformat(m["date"]).date() == today]
    today_workouts = [w for w in user_data["workouts"] if datetime.fromisoformat(w["date"]).date() == today]
    
    total_cal = sum(m["calories"] for m in today_meals)
    total_protein = sum(m.get("protein", 0) for m in today_meals)
    total_workout = sum(w["duration"] for w in today_workouts)
    
    target_cal = user_data["settings"]["target_calories"]
    target_protein = user_data["settings"]["target_protein"]
    
    cal_pct = int(total_cal / target_cal * 100) if target_cal else 0
    protein_pct = int(total_protein / target_protein * 100) if target_protein else 0
    
    cal_bar = "█" * min(10, cal_pct // 10) + "░" * (10 - min(10, cal_pct // 10))
    protein_bar = "█" * min(10, protein_pct // 10) + "░" * (10 - min(10, protein_pct // 10))
    
    meals_list = "\n".join([f"  • {m['name']} - {m['calories']} קל'" for m in today_meals]) or "  אין"
    workouts_list = "\n".join([f"  • {w['type']} - {w['duration']} דק'" for w in today_workouts]) or "  אין"
    
    await update.message.reply_text(
        f"📊 *סיכום יומי - {today.strftime('%d/%m')}*\n\n"
        f"🔥 *קלוריות:* {total_cal}/{target_cal}\n[{cal_bar}] {cal_pct}%\n\n"
        f"💪 *חלבון:* {total_protein}g/{target_protein}g\n[{protein_bar}] {protein_pct}%\n\n"
        f"🏃 *אימון:* {total_workout} דקות\n\n"
        f"🍽️ *ארוחות:*\n{meals_list}\n\n"
        f"💪 *אימונים:*\n{workouts_list}",
        parse_mode='Markdown'
    )

async def week_summary(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    week_ago = datetime.now() - timedelta(days=7)
    
    week_meals = [m for m in user_data["meals"] if datetime.fromisoformat(m["date"]) > week_ago]
    week_workouts = [w for w in user_data["workouts"] if datetime.fromisoformat(w["date"]) > week_ago]
    week_weights = [w for w in user_data["weights"] if datetime.fromisoformat(w["date"]) > week_ago]
    
    total_cal = sum(m["calories"] for m in week_meals)
    avg_cal = int(total_cal / 7) if week_meals else 0
    total_protein = sum(m.get("protein", 0) for m in week_meals)
    total_workout = sum(w["duration"] for w in week_workouts)
    workout_count = len(week_workouts)
    workout_days = len(set(datetime.fromisoformat(w["date"]).date() for w in week_workouts))
    
    weight_change = ""
    if len(week_weights) >= 2:
        diff = week_weights[-1]["value"] - week_weights[0]["value"]
        emoji = "📈" if diff > 0 else "📉" if diff < 0 else "➡️"
        weight_change = f"\n\n⚖️ *שינוי משקל:* {emoji} {diff:+.1f} ק\"ג"
    
    await update.message.reply_text(
        f"📈 *סיכום שבועי*\n\n"
        f"🔥 *קלוריות:* {total_cal:,} (ממוצע: {avg_cal:,}/יום)\n"
        f"💪 *חלבון:* {total_protein}g\n\n"
        f"🏃 *אימונים:* {workout_count} ({total_workout} דק')\n"
        f"📅 *ימים פעילים:* {workout_days}/7"
        f"{weight_change}",
        parse_mode='Markdown'
    )

async def settings(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_data = get_user_data(update.effective_user.id)
    s = user_data["settings"]
    await update.message.reply_text(
        f"⚙️ *הגדרות*\n\n"
        f"🎯 יעד קלוריות: {s['target_calories']}\n"
        f"💪 יעד חלבון: {s['target_protein']}g\n\n"
        f"לשינוי:\n/setcalories 2000\n/setprotein 150",
        parse_mode='Markdown'
    )

async def set_calories(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(context.args[0])
        user_data = get_user_data(update.effective_user.id)
        user_data["settings"]["target_calories"] = target
        save_user_data(update.effective_user.id, user_data)
        await update.message.reply_text(f"✅ יעד קלוריות: {target}")
    except:
        await update.message.reply_text("שימוש: /setcalories 2000")

async def set_protein(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        target = int(context.args[0])
        user_data = get_user_data(update.effective_user.id)
        user_data["settings"]["target_protein"] = target
        save_user_data(update.effective_user.id, user_data)
        await update.message.reply_text(f"✅ יעד חלבון: {target}g")
    except:
        await update.message.reply_text("שימוש: /setprotein 150")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith("ארוחה:") or text.startswith("אכלתי"):
        try:
            parts = text.split(":", 1)[1].strip().split(",")
            name = parts[0].strip()
            calories = int(parts[1].strip()) if len(parts) > 1 else 0
            protein = int(parts[2].strip()) if len(parts) > 2 else 0
            
            user_data = get_user_data(update.effective_user.id)
            user_data["meals"].append({
                "name": name, "calories": calories, "protein": protein,
                "date": datetime.now().isoformat()
            })
            save_user_data(update.effective_user.id, user_data)
            await update.message.reply_text(f"✅ {name}\n🔥 {calories} קל' | 💪 {protein}g")
        except:
            await update.message.reply_text("פורמט: ארוחה: שם, קלוריות, חלבון")
    
    elif text.startswith("אימון:") or text.startswith("התאמנתי"):
        try:
            parts = text.split(":", 1)[1].strip().split(",")
            workout_type = parts[0].strip()
            duration = int(parts[1].strip()) if len(parts) > 1 else 30
            
            user_data = get_user_data(update.effective_user.id)
            user_data["workouts"].append({
                "type": workout_type, "duration": duration,
                "date": datetime.now().isoformat()
            })
            save_user_data(update.effective_user.id, user_data)
            await update.message.reply_text(f"✅ {workout_type}\n⏱️ {duration} דקות")
        except:
            await update.message.reply_text("פורמט: אימון: סוג, דקות")
    
    elif text.startswith("משקל:"):
        try:
            weight = float(text.split(":", 1)[1].strip().replace(",", "."))
            user_data = get_user_data(update.effective_user.id)
            user_data["weights"].append({"value": weight, "date": datetime.now().isoformat()})
            save_user_data(update.effective_user.id, user_data)
            await update.message.reply_text(f"✅ משקל: {weight} ק\"ג")
        except:
            await update.message.reply_text("פורמט: משקל: 75.5")
    
    elif text == "🍽️ הוסף ארוחה":
        return await add_meal_start(update, context)
    elif text == "💪 הוסף אימון":
        return await add_workout_start(update, context)
    elif text == "⚖️ עדכן משקל":
        return await add_weight_start(update, context)
    elif text == "📊 סיכום יומי":
        return await today_summary(update, context)
    elif text == "📈 סיכום שבועי":
        return await week_summary(update, context)
    elif text == "⚙️ הגדרות":
        return await settings(update, context)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("❌ בוטל")
    return ConversationHandler.END

def main():
    if not BOT_TOKEN:
        print("❌ חסר BOT_TOKEN!")
        return
    
    print("🏋️ מתחיל את הבוט...")
    
    app = Application.builder().token(BOT_TOKEN).build()
    
    meal_handler = ConversationHandler(
        entry_points=[
            CommandHandler("meal", add_meal_start),
            MessageHandler(filters.Regex("^🍽️ הוסף ארוחה$"), add_meal_start)
        ],
        states={
            WAITING_MEAL_NAME: [
                CallbackQueryHandler(quick_meal_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, meal_name_received)
            ],
            WAITING_MEAL_CALORIES: [MessageHandler(filters.TEXT & ~filters.COMMAND, meal_calories_received)],
            WAITING_MEAL_PROTEIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, meal_protein_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    workout_handler = ConversationHandler(
        entry_points=[
            CommandHandler("workout", add_workout_start),
            MessageHandler(filters.Regex("^💪 הוסף אימון$"), add_workout_start)
        ],
        states={
            WAITING_WORKOUT_TYPE: [
                CallbackQueryHandler(workout_type_callback),
                MessageHandler(filters.TEXT & ~filters.COMMAND, workout_type_text)
            ],
            WAITING_WORKOUT_DURATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, workout_duration_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    weight_handler = ConversationHandler(
        entry_points=[
            CommandHandler("weight", add_weight_start),
            MessageHandler(filters.Regex("^⚖️ עדכן משקל$"), add_weight_start)
        ],
        states={
            WAITING_WEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, weight_received)],
        },
        fallbacks=[CommandHandler("cancel", cancel)]
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("today", today_summary))
    app.add_handler(CommandHandler("week", week_summary))
    app.add_handler(CommandHandler("settings", settings))
    app.add_handler(CommandHandler("setcalories", set_calories))
    app.add_handler(CommandHandler("setprotein", set_protein))
    
    app.add_handler(meal_handler)
    app.add_handler(workout_handler)
    app.add_handler(weight_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    print("🏋️ הבוט פועל!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()

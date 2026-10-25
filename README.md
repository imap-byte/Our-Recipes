# Our-Recipes · המתכונים שלנו

האתר מופרד לשלושה חלקים:

- **מנוע:** `index.html`, `assets/site.css`, `assets/app.js`, `assets/recipe-loader.js`.
- **נתונים:** `data/recipes.json` (מתכונים, קרדיטים, קטגוריות והפניות), `data/media.json` (מזהי מדיה → נתיבים וטביעות SHA-256), וסכמות JSON.
- **מדיה:** קבצים בינאריים תחת `media/photos/` ו־`media/scans/` בענף `recipe-media`. ה־commit המדויק רשום ב־`data/media-source.json`.

בזמן הבנייה נאספים שלושת החלקים לאתר סטטי אחד. הדפדפן קורא רק כתובות יחסיות לאותו אתר, כולל בפרסום תחת `/Our-Recipes/`. אין תלות ב־raw.githubusercontent.com, ב־CDN חיצוני או בקובצי Base64. שמות המדיה כוללים טביעת תוכן; קובץ חדש אינו דורס גרסה ישנה.

## בדיקה מקומית

```sh
python -m pip install -r requirements-dev.txt
git fetch origin recipe-media
python scripts/build.py --output /tmp/our-recipes-preview
python -m http.server 8000 --bind 127.0.0.1 --directory /tmp/our-recipes-preview
```

יש לבחור תיקיית פלט חדשה בכל בנייה. סקריפט הבנייה מסרב למחוק תיקייה קיימת או לכתוב בתוך מאגר המקור. אם המדיה ב־checkout נפרד, ניתן למסור `--media-root PATH`; הסקריפט מוודא שה־HEAD שלו תואם ל־commit המקובע. הקבצים בענף המנוע לבדם אינם אתר לפרסום: חובה לבנות את חבילת האתר הכוללת גם מדיה.

```sh
python scripts/validate.py --site /tmp/our-recipes-preview
python tests/validation.py --site /tmp/our-recipes-preview
python -m playwright install chromium
python tests/browser.py --site /tmp/our-recipes-preview
```

בדיקת שימור חד־פעמית למיגרציה, מול גרסת המקור השמורה בהיסטוריית Git:

```sh
python tests/preservation.py --site /tmp/our-recipes-preview
```

הבדיקה האחרונה דורשת זהות מלאה למקור ולכן אינה מיועדת לשינויים עתידיים בתוכן. בדיקות התקינות והדפדפן הרגילות נגזרות מהנתונים ואינן מחייבות שינוי מנוע כשמוסיפים מתכון לקטגוריה קיימת.

## פרסום ב־GitHub Pages

ה־workflow ב־`.github/workflows/pages.yml` בונה ומאמת את האתר, מפעיל בדיקות דפדפן, ורק אז מעלה Pages artifact ומפרסם אותו. הוא מפרסם רק את `main`; בדיקות Pull Request אינן מפרסמות. קבצים ותמונות נמסרים יחד באותו artifact, כך שגרסת נתונים אינה מתערבבת עם גרסת מדיה אחרת.

**נדרש ב־Settings → Pages → Build and deployment: Source = GitHub Actions.** פרסום ישיר מתיקיית השורש בענף אינו מתאים למבנה הזה, משום שהמדיה נשמרת בענף נפרד. שינוי ההגדרה אינו מתבצע על ידי הקוד. יש לאמת אותה לפני מיזוג המיגרציה ל־main. ההגדרות לא היו נגישות דרך ה־API בסביבת העבודה ולכן אין בדוח הבטחה שפרסום ציבורי כבר הופעל.

עדכון `recipe-media` לבדו אינו משנה אתר קיים. יש לעדכן את ה־commit המקובע בנתונים בענף המנוע, להריץ את הבדיקות ולפרסם מחדש. גרסאות מדיה ישנות נשארות בהיסטוריה ובנקודת השחזור.

הוספת תוכן: [מדריך תחזוקה](docs/ADDING_RECIPES.md). תוצאות המיגרציה: [דוח בדיקות](docs/MIGRATION-20261025.md).

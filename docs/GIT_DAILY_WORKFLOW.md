# 🔄 Git Daily Workflow

## ทุกวันที่แก้โค้ด (Every Day You Edit Code)

---

## 💻 Dev PC — หลังแก้โค้ดเสร็จ (After editing code)

Open terminal in project folder, then run:

```powershell
git add .
git commit -m "อธิบายสิ่งที่แก้ไข"
git push
```

### ตัวอย่าง commit message:
- `git commit -m "Fix autosync bug"`
- `git commit -m "Add search filter feature"`
- `git commit -m "Update CSS styling"`

---

## 🖥️ Mini PC — ดึงโค้ดล่าสุด (Get latest code)

```powershell
cd "D:\CW\inventory management system"
git pull
```

### ถ้าแก้ Python files (server.py, extract_*.py):
```
1. หยุด server ก่อน (Ctrl+C)
2. git pull
3. เปิด server ใหม่: start_server.bat
```

### ถ้าแก้แค่ HTML/CSS/JS:
```
1. git pull
2. กด Ctrl+F5 ที่ browser (ไม่ต้อง restart server)
```

---

## 📋 Quick Reference (พิมพ์ได้เลย)

```
┌──────────────────────────────────────────────┐
│                DEV PC                        │
│                                              │
│  1. git add .                                │
│  2. git commit -m "what I changed"           │
│  3. git push                                 │
│                                              │
├──────────────────────────────────────────────┤
│                MINI PC                       │
│                                              │
│  1. git pull                                 │
│  2. restart server (ถ้าแก้ .py files)        │
│                                              │
└──────────────────────────────────────────────┘
```

---

## 🔍 คำสั่งที่ใช้บ่อย (Useful Commands)

| คำสั่ง | ใช้ทำอะไร |
|--------|----------|
| `git status` | ดูว่าแก้ไฟล์อะไรไปบ้าง |
| `git diff` | ดูรายละเอียดที่แก้ไข |
| `git log --oneline -10` | ดูประวัติ 10 commits ล่าสุด |
| `git pull` | ดึงโค้ดล่าสุดจาก GitHub |
| `git push` | ส่งโค้ดขึ้น GitHub |

---

## ⚠️ สิ่งที่ต้องจำ (Important Notes)

1. **Push ทุกครั้งที่แก้โค้ดเสร็จ** — อย่าลืม! ไม่งั้น Mini PC จะไม่ได้โค้ดใหม่
2. **Pull ก่อน Push เสมอ** — ถ้าแก้โค้ดบนทั้ง 2 เครื่อง ให้ `git pull` ก่อนเสมอ
3. **Data files ไม่ sync ผ่าน Git** — ไฟล์ `.db`, `.csv`, `.TXT` อยู่แค่ในเครื่อง ไม่ขึ้น GitHub
4. **แก้ Python files → ต้อง restart server** — HTML/CSS/JS แค่ refresh browser

---

## 🚨 แก้ปัญหา (Troubleshooting)

### "error: failed to push"
```powershell
git pull
# แก้ conflict ถ้ามี
git push
```

### "ลืม commit แล้ว push ไม่ได้"
```powershell
git add .
git commit -m "forgot to commit"
git push
```

### "อยากย้อนกลับไฟล์ที่แก้ (ยังไม่ได้ commit)"
```powershell
git checkout -- server.py
```

### "อยากดูว่า commit ก่อนหน้าแก้อะไร"
```powershell
git log --oneline -10
git show abc1234
```

---

> **Document created:** 2026-03-14
> **GitHub Repo:** https://github.com/parinthonc/inventory-management-system

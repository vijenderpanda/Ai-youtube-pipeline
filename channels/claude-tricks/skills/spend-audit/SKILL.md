---
name: spend-audit
description: Totals spending from UPI or bank screenshots, removing rows duplicated by overlapping shots. Use whenever someone shares GPay, PhonePe, Paytm or bank history images, or asks where their money went.
license: CC0-1.0
compatibility: Works anywhere images can be attached to the conversation. Reads transactions with vision only. Ships no scripts, needs no network access, and never writes files.
metadata:
  audience: personal finance, India, UPI apps
  input: screenshots of payment history
  output: chat summary only
---

# Spend Audit

Turn a handful of payment-history screenshots into one honest number and a
short breakdown of where the money went.

The whole job is: read every row, throw away the rows that appear twice
because the screenshots overlap, ignore the rows that are sliced in half at
the edge of a screenshot, group the rest, and say out loud what was thrown
away.

## What this is, and what it is not

This is a **floor**, not an audit. It is the total of the transactions that
are visible in the supplied images and nothing else. It is not a bank
statement, not a complete record of the month, and not financial advice.

Every output must say this in plain words. Never present the total as
complete. Never estimate, extrapolate, annualise, or "fill in the gaps".
Never round a figure that was read exactly.

## Step 0 — Check what arrived

Count the attached images before doing anything else.

- **Zero images** — ask for screenshots of the payment history from GPay,
  PhonePe, Paytm, or the bank app. Do not analyse a typed list instead. This
  skill reports only what is visible in images. Say so and stop.
- **One image** — proceed, but skip Step 3 entirely. A single screenshot
  cannot duplicate itself, so nothing is removed.
- **Two or more** — run every step.

Also check the images are payment history. If someone attaches a single
receipt, a UPI success screen, or a screenshot of a chat, say what was
received and ask for the history list instead.

## Step 1 — Read each image separately

Work through the images **one at a time**, in the order given. Do not merge
anything yet.

For every row that is fully visible, record:

- date (and the time, if the app shows it — the time is the strongest
  de-duplication signal there is)
- payee exactly as written on screen
- amount
- direction: money **sent** or money **received**
- which image it came from, and roughly where in that image (top / middle /
  bottom)

Rules while reading:

- **Read the amount exactly.** Never round, never infer a missing digit. If
  any character of an amount is obscured, blurred, or cut, the row is
  unreadable — send it to the skipped list, do not guess.
- **Relative dates.** GPay and PhonePe often show "Today" and "Yesterday".
  Resolve these only against an absolute date visible elsewhere in the same
  image. If no absolute date is visible anywhere, keep the label as given and
  say in the output that the date range could not be pinned down.
- **Sent versus received matters.** UPI history mixes both. Only money
  **sent** counts as spend. Count the received rows and report the count, but
  never subtract them from the total and never net them off.
- **Not spend, even though it looks like a payment:** wallet top-ups ("Added
  to wallet"), self-transfers between the user's own accounts, credit-card
  bill payments made from the same person's bank, refunds, cashback, and
  failed or pending transactions. Exclude them and count them as excluded.
- If a screenshot shows a running balance, ignore it. Balances are not
  transactions.

For India-specific reading traps — the rupee symbol, lakh digit grouping,
DD/MM dates, Devanagari merchant names, sticky date headers, autopay labels —
read `references/edge-cases.md`.

## Step 2 — Drop the sliced rows

Do this **before** de-duplicating, and do it per image.

A row is sliced when the top or bottom edge of the screenshot cuts through
it: the payee is there but the amount is gone, the amount is there but the
date is gone, or the text is visually clipped.

- Never guess what a sliced row says.
- Delete that instance and add it to the skipped list.

This ordering is deliberate and it does real work. When someone scrolls and
shoots, a row that is sliced at the bottom of image 1 is usually complete in
the middle of image 2. Dropping the sliced copy first means the complete copy
survives Step 3 and the transaction is still counted — once.

## Step 3 — Remove the duplicates

Overlapping screenshots are the single biggest source of error in this task.
A measured test on two overlapping shots inflated the total by 7%. Apply
these rules in order.

**The key is (date + payee + amount).**

1. **Two rows from the same image are never duplicates of each other.** One
   screenshot cannot show the same transaction twice. If a person paid the
   same shop the same amount twice on the same day, and both rows are in one
   image, both are real. Keep both.
2. **Two rows from different images with the same key are the same
   transaction** — unless a visible time differs. Keep one, count one.
3. **When times are visible, the time decides.** Same key, different times →
   two separate payments, keep both. Same key, same time → one payment.
4. **When times are not visible and the key matches across images, treat it
   as one payment.** This can under-count a genuine repeat payment. That is
   the correct direction to be wrong: the output is a floor, so erring low is
   honest and erring high is not.
5. **Confirm the overlap before trusting it.** Two images overlap when a run
   of consecutive rows appears in both. Find that shared run. If the images
   cover completely separate date ranges with no shared rows, there is
   nothing to de-duplicate and any identical-looking rows are real repeats.
6. **Payee text may differ between a UPI app and a bank statement** for the
   same payment ("Swiggy" versus "UPI/SWIGGYIN/4471"). If the user mixed
   sources, match on date plus amount and treat a strong merchant-name
   fragment as a match — then say plainly in the output that mixing a bank
   statement with a UPI app makes double-counting likely and that the safest
   run uses one source only.

Keep a running count of how many rows were removed. This number goes in the
output. It is the proof the work was done.

## Step 4 — Categorise

Put every surviving row into exactly one of these eight:

`Food delivery` · `Groceries` · `Shopping` · `Travel` ·
`Bills & recharge` · `Going out` · `People` · `Other`

Use `references/categories.md` for the merchant lookup. It covers the common
Indian merchants and the rules for the ones that are ambiguous.

If a merchant is genuinely unrecognisable, put it in `Other`. Never invent a
category and never guess a merchant's business from a partial name.

## Step 5 — Protect the people

This rule has no exceptions.

Person-to-person transfers — anything paid to an individual's name, a phone
number, or a personal UPI handle — collapse into **one single line called
"People"** with a total and a count.

- Never print a person's name in the output.
- Never print a phone number or a UPI ID.
- Never break People down by recipient, not even as "your top recipient".
- Never say how many different people were paid.
- If the user explicitly asks who they paid, answer from the images in that
  reply, but keep the summary itself clean.

These are third parties who did not consent to appear in a spending report,
and the report is the thing people screenshot and share.

## Step 6 — Find the one surprising line

Pick exactly one, and say why it is surprising. There are only two valid
reasons:

- **Frequency** — it happened far more often than anything else. ("8 of your
  18 payments.")
- **Size relative to the rest** — one category or one merchant is a large
  share of the total. ("A third of everything.")

Support it with the arithmetic actually done: count, share of total, average
per payment. If nothing genuinely stands out, say that — a flat month is a
real result, and inventing drama is exactly what this skill exists to avoid.

Never make the People line the surprising one. See Step 5.

## Step 7 — Check whether the range is complete

Look at the oldest and newest rows.

Ask for more screenshots when:

- the **oldest** row sits at the very top of the oldest image — the list
  almost certainly continues further back
- the **newest** row sits at the very bottom of the newest image
- there is a gap of several days in the middle with no transactions, which
  usually means a missing screenshot rather than a quiet week
- the range covers less than a week when the user asked about a month

Ask for one specific thing ("one more screenshot scrolled further back"), not
a vague "send more".

## Step 8 — Write it for a phone

The output is read on a phone screen, one thumb, moving. Shape it that way.

- **Biggest number first**, on line one, with the floor caveat attached to it.
- **No tables.** No aligned columns — the chat font is proportional, so
  alignment breaks and turns into noise.
- One category per line, biggest to smallest, as `Name — ₹amount · N payments`.
- Short lines. Nothing that wraps three times.
- Whole rupees. Drop the paise.
- Indian digit grouping: ₹11,195 and ₹1,20,000.
- No emoji, no exclamation marks, no praise, no scolding. Report, do not judge.
- Never list individual transactions unless asked. The summary is the product.

### Output template

```
₹<total> spent — and that's a floor, not a full audit.
<N> payments, <date range>, from <N> screenshots.

Where it went
• <Category> — ₹<amount> · <N> payments
• <Category> — ₹<amount> · <N> payments
...

Most surprising
<One category or merchant, plus why: frequency or share. Two or three short lines.>

What I skipped
• <N> rows appeared twice across overlapping screenshots — counted once
• <N> rows were cut off at a screenshot edge — skipped, not guessed
• <N> money-received rows — not counted as spend

<Range check, only if incomplete: what's missing and the one screenshot to send.>

This is only what's in these images. Your real total is higher.
```

Drop any "What I skipped" bullet whose count is zero. Never drop the closing
floor line, and never soften it.

## Hard rules

- Never present the total as complete, final, or bank-grade.
- Never guess a digit, a date, or a merchant.
- Never name a person, a phone number, or a UPI handle in the summary.
- Never net received money against spend.
- Never give advice about what to cut, unless asked. Report the numbers.
- Never claim a category is "too high" — that is the user's call, not this
  skill's.
- Always state how many duplicates were removed, even when the answer is zero.

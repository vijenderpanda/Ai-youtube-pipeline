# Reading traps in Indian payment screenshots

Load this while reading rows (Step 1) or when something on screen does not
parse cleanly.

## Amounts

- The symbol may be `₹`, `Rs`, `Rs.`, `INR`, or absent entirely. All mean
  rupees. Never convert to any other currency.
- Indian digit grouping puts the first comma after three digits and then
  every two: `1,000` · `10,000` · `1,00,000` (one lakh) · `10,00,000`.
  A row reading `1,20,000` is one lakh twenty thousand, not one hundred
  twenty thousand written oddly.
- Paise appear as `.00` or `.50`. Keep them while adding, drop them in the
  output.
- Sign conventions differ by app and are the only reliable direction marker
  on some screens:
  - GPay: money sent has no prefix, money received is often green with a `+`.
  - PhonePe: red `-` or "Debited", green `+` or "Credited".
  - Paytm: "Paid to" versus "Received from", plus colour.
  - Bank statements: separate Debit and Credit columns, or `Dr` / `Cr`.
  If direction is genuinely ambiguous on a row, skip that row and report it.
  Guessing direction is worse than dropping the row.
- A number next to the word "Balance" is not a transaction.

## Dates

- Formats seen: `12/08/26`, `12-08-2026`, `12 Aug`, `12 Aug 2026`,
  `Aug 12`. Indian apps are DD/MM. `05/08` is 5 August, not 8 May.
- **Relative labels.** "Today", "Yesterday", "This week", "Last month" are
  headers, not dates. Resolve them only against an absolute date visible in
  the same image. If nothing absolute is visible in any image, keep the label
  and say in the output that the range could not be pinned down.
- **Sticky date headers.** GPay and PhonePe pin the current date group to the
  top of the scroll. A pinned header can be the header for rows that are not
  actually under it in the underlying list. Trust the header that sits
  directly above a row in the list flow, not a floating one at the very top
  edge.
- Month dividers ("August", "July") are headers. They are not transactions.
- Do not assume a year. If no year is visible, do not print one.

## Merchant names

- Bank statements mangle names: `UPI/SWIGGYIN/447102/Payment`,
  `POS 4471 AMAZON`, `NEFT-ZOMATO LTD-XXXX`. Extract the recognisable
  fragment for categorisation, but print the name as the user's app shows it
  where possible.
- Devanagari and other Indic scripts appear for local shops. Read them,
  categorise on meaning, and print the name as shown.
- Emoji and app badges sometimes sit inside the payee cell. Ignore them.
- A merchant may show as a person's name if it is a sole proprietor using a
  personal UPI handle. When there is any doubt, treat it as **People** — the
  privacy-preserving choice is the correct default.

## Rows that are not spend

Exclude and count these, do not subtract them:

- "Added to wallet" / "Wallet top-up" / "Added money" — the spend happens
  when the wallet is used, so counting the top-up too is double counting.
- "Self transfer", transfers to the user's own second account.
- Credit-card bill payments made from the user's own bank. The card spends
  are the real transactions, and they are not in this screenshot.
- Refunds, reversals, cashback, rewards, "Money received".
- "Failed", "Pending", "Processing", "Expired", "Cancelled".
- Autopay mandate **setup** notices with no amount debited.
- Split-bill requests that were sent but not paid.

## Crop and capture damage

A row is unusable when any of these is true:

- text is visually clipped by the top or bottom edge of the image
- the payee is present but the amount is off-frame, or vice versa
- a notification banner, keyboard, or navigation bar covers part of the row
- the row is behind a search overlay or a half-open bottom sheet
- the screenshot is too low-resolution to read a digit with certainty

Skip it. Add it to the skipped count. Do not reconstruct it from a
neighbouring image unless that neighbouring image shows the row complete, in
which case the complete copy is the one that counts and this instance simply
disappears.

## Mixed sources

If the user supplies both a UPI app and a bank statement, the same payment
appears in both with different payee text. Match on date plus amount, treat a
strong merchant fragment as confirmation, and state in the output that mixing
sources makes double counting likely. The clean run uses one source.

## Capture advice worth giving once

If the screenshots overlap heavily, or rows are sliced, add one line at the
end of the output: scroll by a full screen between shots rather than a small
nudge, and keep a date visible in every shot. That single habit removes most
duplicates before they are ever created.

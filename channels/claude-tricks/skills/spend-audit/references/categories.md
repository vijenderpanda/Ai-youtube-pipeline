# Merchant to category lookup (India)

Eight categories, no others:
`Food delivery` · `Groceries` · `Shopping` · `Travel` ·
`Bills & recharge` · `Going out` · `People` · `Other`

## Food delivery
Swiggy, Zomato, Zomato Gold/District (food orders), EatSure, Faasos,
Behrouz, Box8, Domino's (delivery), Pizza Hut (delivery), McDelivery,
KFC (delivery), Licious, FreshToHome, Country Delight, Milkbasket,
Curefoods, Wow! Momo, Chaayos delivery, any "…Food Pvt Ltd" aggregator.

Note: Swiggy Instamart and Zomato's grocery arm are **Groceries**, not Food
delivery, when the screenshot labels them as such. If the row only says
"Swiggy", leave it in Food delivery — do not guess.

## Groceries
Blinkit, Zepto, Swiggy Instamart, BigBasket, BBnow, DMart, Reliance Fresh,
Reliance Smart, More Retail, Spencer's, Star Bazaar, Nature's Basket,
JioMart, Amazon Fresh, Otipy, local kirana stores, vegetable/fruit vendors,
dairy and milk booths, "General Store", "Provision Store", "Kirana".

## Shopping
Amazon, Flipkart, Myntra, Ajio, Meesho, Nykaa, Tata CLiQ, Snapdeal, Croma,
Reliance Digital, Vijay Sales, Decathlon, Lenskart, FirstCry, Pepperfry,
Urban Ladder, IKEA, H&M, Zara, Westside, Max, Pantaloons, Shoppers Stop,
Boat, Apple, Samsung Store, any clothing/electronics/home retailer.

## Travel
Uber, Ola, Rapido, Namma Yatri, BluSmart, InDrive, Yulu, Bounce,
IRCTC, RedBus, AbhiBus, MakeMyTrip, Goibibo, Cleartrip, EaseMyTrip, Ixigo,
Yatra, IndiGo, Air India, Akasa, SpiceJet, Vistara,
OYO, Airbnb, Treebo, FabHotels,
metro card recharges (DMRC, Chalo, ONDC transit), toll and FASTag,
petrol and diesel: Indian Oil, HP, HPCL, Bharat Petroleum, BPCL, Shell,
Nayara, Jio-bp, "Fuel Station", "Petrol Pump".

## Bills & recharge
Mobile and broadband: Jio, Airtel, Vi, Vodafone Idea, BSNL, ACT Fibernet,
Hathway, Excitel, Tata Play Fiber.
Electricity and utilities: BESCOM, MSEDCL, Adani Electricity, Tata Power,
BSES, TNEB, PSPCL, KSEB, any "…Electricity Board", Mahanagar Gas,
Indraprastha Gas, Gujarat Gas, water board, municipal tax.
DTH and TV: Tata Play, Dish TV, Airtel Digital TV, Sun Direct.
Subscriptions and OTT: Netflix, Spotify, JioHotstar, Prime, YouTube Premium,
Apple, Google One, Adobe, Canva, ChatGPT, gym memberships on autopay.
Money apps that are bill rails: CRED, Paytm bill pay, PhonePe recharge,
BBPS. Categorise by **what was paid**, not by the app used to pay it.
Insurance premiums, loan EMIs, rent paid to a company or society.

## Going out
Restaurants, cafés, bars and pubs paid in person (Starbucks, Third Wave,
Blue Tokai, Chaayos, Barista, Social, Toit, local restaurant names),
BookMyShow, PVR, INOX, Cinepolis, Carnival, amusement parks, museums,
event and concert tickets, bowling, gaming zones.

## People
Any payee that is a person, not a business:
- a human name ("Rahul S", "Amit Kumar", "Priya")
- a bare phone number
- a personal UPI handle (`name@okaxis`, `9876543210@ybl`, `@paytm`,
  `@ibl`, `@apl`) with no business name shown
- "Sent to <name>" / "Paid to <name>" where the name is not a known merchant
- an unlabelled bank account transfer to an individual

Collapse to one line. Never name anyone. See Step 5 of SKILL.md.

## Other
Everything genuinely unrecognisable, plus:
medical and pharmacy (Apollo, PharmEasy, Tata 1mg, Netmeds, Practo,
hospitals, diagnostic labs), education and courses, salons and grooming,
courier and postal, repairs, donations, government fees, ATM withdrawals.

Cash withdrawn at an ATM is **Other**, not a category guess. The money left
the account but where it went is not visible.

## Ambiguity rules

1. **The row's own words beat this list.** If the screenshot says "Swiggy
   Instamart", it is Groceries even though Swiggy is listed under Food
   delivery.
2. **Categorise the destination, not the rail.** Paytm, PhonePe, GPay, CRED
   and BharatPe are payment apps. A recharge through Paytm is Bills &
   recharge. A shop paid through Paytm is Shopping. Never create a "Paytm"
   category.
3. **A partial name is not a match.** "SWIG" is not enough. Unrecognisable
   goes to Other.
4. **One category per transaction.** Never split an amount across two.
5. **Never invent a ninth category**, however tempting. If a real cluster
   does not fit the eight, mention it in one sentence under the surprising
   line instead.

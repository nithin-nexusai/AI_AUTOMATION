"""System prompts for the CHICX WhatsApp bot.

This module contains the system prompts that define the bot's personality,
capabilities, and behavior guidelines. The bot is multilingual with support
for English, Tamil, Malayalam, and Hindi.

Key characteristics:
- READ-ONLY: Users can browse products and track orders but cannot purchase through the bot
- Friendly, helpful tone representing the CHICX brand
- Multilingual: English, Tamil (Tanglish), Malayalam (Manglish), Hindi (Hinglish)
- Focus on women's fashion e-commerce
"""


# Main system prompt for the WhatsApp bot assistant
WHATSAPP_SYSTEM_PROMPT = """You are CHICX Assistant, a friendly and helpful AI customer service representative for CHICX, a Direct-to-Consumer (D2C) women's fashion e-commerce brand in India.

## Your Identity
- Name: CHICX Assistant
- Brand: CHICX - Trendy, affordable women's fashion
- Personality: Warm, helpful, professional yet friendly
- Language: Multilingual - fluent in English, Tamil, Malayalam, Hindi and code-switching variants (Tanglish, Manglish, Hinglish)

## Your Capabilities
You can help customers with:
1. **Product Discovery** - Search and browse the CHICX catalog (sarees, kurtis, dresses, tops, ethnic wear, western wear, etc.)
2. **Product Information** - Provide details about specific products (price, description, sizes, colors, materials)
3. **Order Tracking** - Check order status, tracking information, and delivery updates
4. **Order History** - Help customers view their past orders
5. **FAQ & Support** - Answer questions about shipping, returns, payments, sizing, and policies

## IMPORTANT LIMITATIONS - READ-ONLY BOT
- You CANNOT add items to cart
- You CANNOT process purchases or payments
- You CANNOT modify orders
- You CANNOT create accounts

When customers want to buy something, ALWAYS direct them to the CHICX website with the product URL. Say something like:
- "I'd love to help you purchase this! Please visit [product_url] to add it to your cart and complete your order."
- "Great choice! You can buy this at chicx.in - I'll share the direct link for you."

## Language Guidelines

### English
Use clear, friendly English for customers who message in English. Keep sentences concise and helpful.

### Tamil (தமிழ்)
When customers message in Tamil, respond in Tamil. Use proper Tamil script when appropriate.
Example: "வணக்கம்! CHICX-ல் உங்களை வரவேற்கிறோம். நான் உங்களுக்கு எப்படி உதவ முடியும்?"

### Tanglish (Tamil-English Code-Switching)
Many customers naturally mix Tamil and English. Mirror their style:
- "Hi! Enna help venumaa?" (What help do you need?)
- "Super choice! Itha website la order pannunga" (Order this on the website)
- "Unga order shipped aagiduchu! Tracking number share pannuren" (Your order is shipped! I'll share the tracking number)

### Malayalam (മലയാളം)
When customers message in Malayalam, respond in Malayalam.
Example: "നമസ്കാരം! CHICX-ലേക്ക് സ്വാഗതം. എനിക്ക് നിങ്ങളെ എങ്ങനെ സഹായിക്കാനാകും?"

### Manglish (Malayalam-English Code-Switching)
Mix Malayalam and English naturally:
- "Hi! Enthu help venam?" (What help do you need?)
- "Super choice! Ithu website-il order cheyyu" (Order this on the website)
- "Ningalude order shipped aayi! Tracking number share cheyyaam" (Your order is shipped! I'll share the tracking number)

### Hindi (हिंदी)
When customers message in Hindi, respond in Hindi.
Example: "नमस्ते! CHICX में आपका स्वागत है। मैं आपकी कैसे मदद कर सकता हूं?"

### Hinglish (Hindi-English Code-Switching)
Mix Hindi and English naturally:
- "Hi! Kya help chahiye?" (What help do you need?)
- "Super choice! Ise website pe order karo" (Order this on the website)
- "Aapka order shipped ho gaya! Tracking number share karta hoon" (Your order is shipped! I'll share the tracking number)

### Language Detection
- If the customer messages in Tamil script, respond in Tamil
- If the customer messages in Malayalam script, respond in Malayalam
- If the customer messages in Hindi/Devanagari script, respond in Hindi
- If they use Tanglish/Manglish/Hinglish, respond in the same style
- If they use English, respond in English
- When unsure, default to English

## Conversation Guidelines

### Greeting
Start conversations warmly:
- "Hi! Welcome to CHICX! I'm here to help you discover amazing fashion. What are you looking for today?"
- "வணக்கம்! CHICX-க்கு welcome! How can I help you?"

### Product Recommendations
When showing products:
- Highlight key features (material, style, occasion)
- Always mention the price
- Share the product URL for purchase
- Suggest related items when appropriate

### Order Tracking
When helping with orders:
- Ask for the order ID if not provided
- Explain the current status clearly
- Provide estimated delivery when available
- Share tracking links when shipment is in transit

### Handling Complaints
- Acknowledge the customer's concern
- Apologize for any inconvenience
- Provide relevant information or solutions
- For complex issues, provide customer support contact: support@chicx.in

### Ending Conversations
- Thank them for choosing CHICX
- Offer additional help if needed
- Encourage them to visit the website for purchases

## Tool Usage Guidelines

Use your tools effectively:

1. **search_products**: Use when customer asks about products, categories, or price ranges
   - Example: "Show me sarees under 2000"
   - Example: "Looking for party dresses"

2. **get_product_details**: Use when customer wants more info about a specific product
   - Always share the product_url with the details

3. **get_order_status**: Use when customer asks about their order
   - Ask for order ID if not provided
   - Explain status in customer-friendly terms

4. **get_order_history**: Use when customer wants to see past orders
   - The user is identified by their WhatsApp phone number

5. **search_faq**: Use for policy questions, how-to questions, general queries
   - Topics: shipping, returns, sizing, payment, account, etc.
   - When FAQs are found, answer DIRECTLY using the FAQ content - don't add extra disclaimers
   - Only suggest contacting support if no relevant FAQ is found

## Response Format
- Keep responses concise - WhatsApp users prefer shorter messages
- Use emojis sparingly and appropriately (1-2 per message max)
- Break long responses into multiple short paragraphs
- Always provide actionable next steps
- Include relevant links when suggesting purchases

## Brand Voice Examples

Good responses:
- "I found some beautiful silk sarees for you! Here are the top picks..."
- "Unga order Chennai reach aagiduchu! Tomorrow delivery expect pannunga."
- "The kurti comes in sizes S, M, L, XL. Based on our sizing guide, if you usually wear M, go with M here too!"

Avoid:
- Overly formal corporate language
- Very long paragraphs
- Making promises about delivery times you can't guarantee
- Discussing competitor brands

## Safety & Privacy
- Never ask for passwords or sensitive payment info
- Only discuss orders that belong to the customer's phone number
- Don't share customer information with third parties
- Direct all payment/checkout activities to the secure website

Remember: Your goal is to provide excellent customer service while guiding users to complete purchases on the CHICX website. Be helpful, friendly, and make every interaction a positive experience!"""


# Shorter system prompt for voice agent (Bolna)
VOICE_SYSTEM_PROMPT = """You are CHICX Assistant, a helpful voice assistant for CHICX women's fashion.

Key points:
- Be conversational and natural for voice
- Keep responses SHORT (under 30 seconds when spoken)
- Speak in the customer's language (English, Tamil, or Tanglish)
- Help with product search, order tracking, and FAQs
- For purchases, tell them to visit chicx.in

IMPORTANT: You cannot process purchases. Always direct customers to the website.

Speak clearly and warmly. Ask clarifying questions when needed."""


# Error response templates
ERROR_RESPONSES = {
    "product_not_found": {
        "en": "I couldn't find that product. It might be out of stock or the ID might be incorrect. Would you like me to search for similar items?",
        "ta": "அந்த பொருளை கண்டுபிடிக்க முடியவில்லை. இது stock இல்லையோ அல்லது ID தவறாக இருக்கலாம். இதே மாதிரியான பொருட்களை தேட வேண்டுமா?",
        "tanglish": "Sorry, antha product kandupidikka mudiyala. Stock illa or wrong ID irukkalaam. Similar items search pannalama?",
        "ml": "ആ ഉൽപ്പന്നം കണ്ടെത്താനായില്ല. സ്റ്റോക്കില്ല അല്ലെങ്കിൽ ID തെറ്റായിരിക്കാം. സമാന ഉൽപ്പന്നങ്ങൾ തിരയണോ?",
        "manglish": "Sorry, aa product kandilla. Stock illa or wrong ID aayirikkum. Similar items search cheyyano?",
        "hi": "वह प्रोडक्ट नहीं मिला। शायद स्टॉक में नहीं है या ID गलत है। क्या मैं समान आइटम खोजूं?",
        "hinglish": "Sorry, wo product nahi mila. Stock mein nahi hai ya wrong ID ho sakta hai. Similar items search karoon?",
    },
    "order_not_found": {
        "en": "I couldn't find an order with that ID. Please check the order ID from your confirmation email or SMS. It usually starts with 'CHX'.",
        "ta": "அந்த order ID-யில் எந்த order-ம் இல்லை. Confirmation email-ல் இருந்து order ID-யை check பண்ணுங்க.",
        "tanglish": "Antha order ID la order illa. Confirmation email la iruntha order ID check pannunga, 'CHX' la start aagum.",
        "ml": "ആ order ID-യിൽ order കണ്ടെത്തിയില്ല. Confirmation email-ൽ നിന്ന് order ID പരിശോധിക്കുക.",
        "manglish": "Aa order ID-yil order kandilla. Confirmation email-il ninn order ID check cheyyu, 'CHX'-il start aakum.",
        "hi": "उस ID से कोई ऑर्डर नहीं मिला। कृपया अपने confirmation email या SMS से order ID देखें।",
        "hinglish": "Us order ID pe order nahi mila. Confirmation email se order ID check karo, 'CHX' se start hota hai.",
    },
    "no_orders": {
        "en": "I don't see any orders linked to your phone number yet. Have you made a purchase on chicx.in?",
        "ta": "உங்க phone number-ல orders எதுவும் இல்லை. chicx.in-ல purchase பண்ணிருக்கீங்களா?",
        "tanglish": "Unga phone number la orders onnum illa. chicx.in la purchase pannirukkeengala?",
        "ml": "നിങ്ങളുടെ phone number-ൽ orders ഒന്നും കാണുന്നില്ല. chicx.in-ൽ purchase ചെയ്തിട്ടുണ്ടോ?",
        "manglish": "Ningalude phone number-il orders onnum illa. chicx.in-il purchase cheythittundo?",
        "hi": "आपके फ़ोन नंबर से कोई ऑर्डर नहीं दिख रहा। क्या आपने chicx.in पर खरीदारी की है?",
        "hinglish": "Aapke phone number pe orders nahi dikh rahe. chicx.in pe purchase kiya hai?",
    },
    "search_no_results": {
        "en": "I couldn't find products matching your search. Try different keywords or browse our categories!",
        "ta": "உங்க search-க்கு matching products இல்லை. வேற keywords try பண்ணுங்க!",
        "tanglish": "Unga search ku matching products illa. Vera keywords try pannunga or categories browse pannunga!",
        "ml": "നിങ്ങളുടെ search-ന് matching products ഇല്ല. മറ്റ് keywords try ചെയ്യൂ!",
        "manglish": "Ningalude search-nu matching products illa. Vere keywords try cheyyu or categories browse cheyyu!",
        "hi": "आपकी खोज से मिलते जुलते प्रोडक्ट नहीं मिले। अलग keywords try करें!",
        "hinglish": "Aapki search ke matching products nahi mile. Alag keywords try karo ya categories browse karo!",
    },
    "faq_not_found": {
        "en": "I don't have specific information about that. For detailed help, please email support@chicx.in or call our helpline.",
        "ta": "இது பற்றி specific information என்கிட்ட இல்லை. support@chicx.in-க்கு email பண்ணுங்க.",
        "tanglish": "Ithu pathi specific info en kitta illa. support@chicx.in ku email pannunga.",
        "ml": "ഇതിനെ കുറിച്ച് specific information എന്റെ കയ്യിൽ ഇല്ല. support@chicx.in-ലേക്ക് email ചെയ്യുക.",
        "manglish": "Ithine kurichu specific info ente kayil illa. support@chicx.in-lekk email cheyyu.",
        "hi": "इसके बारे में मेरे पास specific जानकारी नहीं है। support@chicx.in पर email करें।",
        "hinglish": "Iske baare mein mere paas specific info nahi hai. support@chicx.in pe email karo.",
    },
    "general_error": {
        "en": "I'm having trouble processing that right now. Please try again in a moment or contact support@chicx.in for help.",
        "ta": "இப்போ சிக்கல் இருக்கு. கொஞ்ச நேரம் கழித்து try பண்ணுங்க.",
        "tanglish": "Ippo oru sikal iruku. Konjam wait panni try pannunga or support@chicx.in contact pannunga.",
        "ml": "ഇപ്പോൾ ഒരു പ്രശ്നമുണ്ട്. കുറച്ച് കഴിഞ്ഞ് try ചെയ്യുക.",
        "manglish": "Ippo oru problem und. Kurach kazhinjitt try cheyyu or support@chicx.in contact cheyyu.",
        "hi": "अभी कुछ समस्या है। कुछ देर बाद फिर try करें।",
        "hinglish": "Abhi kuch problem hai. Thodi der baad try karo ya support@chicx.in contact karo.",
    },
}


# Status descriptions for order tracking
ORDER_STATUS_DESCRIPTIONS = {
    "placed": {
        "en": "Your order has been placed successfully! We're preparing it for dispatch.",
        "ta": "உங்க order successfully place ஆயிடுச்சு! Dispatch-க்கு prepare பண்றோம்.",
        "tanglish": "Unga order place aayiduchu! Dispatch ku prepare panrom.",
        "ml": "നിങ്ങളുടെ order successfully place ആയി! Dispatch-ന് prepare ചെയ്യുന്നു.",
        "manglish": "Ningalude order place aayi! Dispatch-nu prepare cheyyunnu.",
        "hi": "आपका ऑर्डर सफलतापूर्वक place हो गया! Dispatch के लिए तैयार कर रहे हैं।",
        "hinglish": "Aapka order place ho gaya! Dispatch ke liye prepare kar rahe hain.",
    },
    "confirmed": {
        "en": "Great news! Your order is confirmed and being packed.",
        "ta": "நல்ல செய்தி! உங்க order confirm ஆயிடுச்சு, packing நடக்குது.",
        "tanglish": "Good news! Unga order confirmed, packing nadakuthu.",
        "ml": "നല്ല വാർത്ത! നിങ്ങളുടെ order confirm ആയി, packing നടക്കുന്നു.",
        "manglish": "Good news! Ningalude order confirmed, packing nadakkunnu.",
        "hi": "अच्छी खबर! आपका ऑर्डर confirm हो गया, packing हो रही है।",
        "hinglish": "Good news! Aapka order confirmed, packing ho rahi hai.",
    },
    "shipped": {
        "en": "Your order is on its way! It has been shipped and is in transit.",
        "ta": "உங்க order ship ஆயிடுச்சு! வழியில் இருக்கு.",
        "tanglish": "Unga order ship aagiduchu! Transit la iruku.",
        "ml": "നിങ്ങളുടെ order ship ആയി! വഴിയിലാണ്.",
        "manglish": "Ningalude order ship aayi! Transit-il aanu.",
        "hi": "आपका ऑर्डर ship हो गया! रास्ते में है।",
        "hinglish": "Aapka order ship ho gaya! Transit mein hai.",
    },
    "out_for_delivery": {
        "en": "Exciting! Your order is out for delivery and will reach you today.",
        "ta": "இன்னைக்கே deliver ஆகும்! Delivery-க்கு கிளம்பிடுச்சு.",
        "tanglish": "Innaike varum! Out for delivery aagiduchu.",
        "ml": "ഇന്ന് തന്നെ deliver ആകും! Delivery-ക്ക് പുറപ്പെട്ടു.",
        "manglish": "Innu thanne varum! Out for delivery aayi.",
        "hi": "आज ही deliver होगा! Delivery के लिए निकल गया।",
        "hinglish": "Aaj hi aayega! Out for delivery ho gaya.",
    },
    "delivered": {
        "en": "Your order has been delivered! Hope you love your new fashion finds!",
        "ta": "உங்க order deliver ஆயிடுச்சு! Enjoy பண்ணுங்க!",
        "tanglish": "Unga order deliver aagiduchu! Enjoy pannunga!",
        "ml": "നിങ്ങളുടെ order deliver ആയി! Enjoy ചെയ്യൂ!",
        "manglish": "Ningalude order deliver aayi! Enjoy cheyyu!",
        "hi": "आपका ऑर्डर deliver हो गया! Enjoy करें!",
        "hinglish": "Aapka order deliver ho gaya! Enjoy karo!",
    },
    "cancelled": {
        "en": "This order has been cancelled. If you have questions about the refund, please check your email or contact support.",
        "ta": "இந்த order cancel ஆயிடுச்சு. Refund பற்றி email check பண்ணுங்க.",
        "tanglish": "Intha order cancel aagiduchu. Refund pathi email check pannunga.",
        "ml": "ഈ order cancel ആയി. Refund-നെ കുറിച്ച് email check ചെയ്യുക.",
        "manglish": "Ee order cancel aayi. Refund-ne kurichu email check cheyyu.",
        "hi": "यह ऑर्डर cancel हो गया। Refund के बारे में email check करें।",
        "hinglish": "Ye order cancel ho gaya. Refund ke baare mein email check karo.",
    },
}


def get_system_prompt(channel: str = "whatsapp") -> str:
    """Get the appropriate system prompt for a channel.

    Args:
        channel: The channel type - "whatsapp" or "voice"

    Returns:
        The system prompt string for the specified channel.
    """
    if channel == "voice":
        return VOICE_SYSTEM_PROMPT
    return WHATSAPP_SYSTEM_PROMPT


def get_error_response(error_type: str, language: str = "en") -> str:
    """Get a localized error response.

    Args:
        error_type: Type of error (e.g., "product_not_found", "order_not_found")
        language: Language code - "en", "ta", or "tanglish"

    Returns:
        The localized error message string.
    """
    if error_type not in ERROR_RESPONSES:
        error_type = "general_error"

    responses = ERROR_RESPONSES[error_type]
    return responses.get(language, responses["en"])


def get_order_status_description(status: str, language: str = "en") -> str:
    """Get a customer-friendly order status description.

    Args:
        status: The order status (e.g., "shipped", "delivered")
        language: Language code - "en", "ta", or "tanglish"

    Returns:
        Human-readable status description in the specified language.
    """
    status_lower = status.lower()
    if status_lower not in ORDER_STATUS_DESCRIPTIONS:
        return f"Order status: {status}"

    descriptions = ORDER_STATUS_DESCRIPTIONS[status_lower]
    return descriptions.get(language, descriptions["en"])

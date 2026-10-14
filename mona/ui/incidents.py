"""Training failures: real problems from MONA's training run, and how to handle them.

Every case really happened while MONA was being built. The learner picks what they would do (1, 2 or 3),
gets honest feedback, then sees what was actually done and the engineering lesson behind it.
"""
from rich.text import Text
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, VerticalScroll
from textual.screen import Screen
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from .text import register
from .widgets import Avatar

register({
    "inc_title": {"en": "Training failures: what goes wrong, and what to do", "hi": "ट्रेनिंग की गड़बड़ियाँ: क्या बिगड़ता है, और क्या करें",
                  "hinglish": "Training failures: kya bigadta hai, aur kya karein"},
    "inc_explain": {
        "en": "{addr}, training a model is mostly about what goes wrong. Each problem here really happened while MONA was trained. Read the symptom, choose what you would do (1, 2 or 3), then see what was done and why.",
        "hi": "{addr}, मॉडल ट्रेन करना ज़्यादातर गड़बड़ियाँ सँभालना है। यहाँ की हर समस्या MONA की ट्रेनिंग के दौरान सच में हुई। लक्षण पढ़िए, चुनिए आप क्या करते (1, 2 या 3), फिर देखिए क्या किया गया और क्यों।",
        "hinglish": "{addr}, model train karna zyadatar gadbadiyan sambhalna hai. Yahan ki har problem MONA ki training ke dauran sach mein hui. Symptom padho, chuno aap kya karte (1, 2 ya 3), phir dekho kya kiya gaya aur kyun.",
    },
    "inc_choose": {"en": "What would you do, {addr}? Press 1, 2 or 3", "hi": "आप क्या करते, {addr}? 1, 2 या 3 दबाइए",
                   "hinglish": "Aap kya karte, {addr}? 1, 2 ya 3 dabao"},
    "inc_good": {"en": "✅ Sound engineering, {addr}!", "hi": "✅ सही इंजीनियरिंग, {addr}!", "hinglish": "✅ Sahi engineering, {addr}!"},
    "inc_ok": {"en": "🤔 Possible, but there's a better move.", "hi": "🤔 हो सकता है, पर बेहतर रास्ता है।",
               "hinglish": "🤔 Ho sakta hai, par behtar raasta hai."},
    "inc_bad": {"en": "⚠️ Risky call.", "hi": "⚠️ जोखिम भरा फ़ैसला।", "hinglish": "⚠️ Risky faisla."},
    "inc_real": {"en": "What was actually done:", "hi": "असल में क्या किया गया:", "hinglish": "Asal mein kya kiya gaya:"},
    "inc_lesson": {"en": "The general lesson:", "hi": "आम सबक़:", "hinglish": "General sabak:"},
    "inc_score": {"en": "{a} of {b} answers matched good practice", "hi": "{b} में से {a} जवाब अच्छे अभ्यास से मेल खाए",
                  "hinglish": "{b} mein se {a} answers good practice se match hue"},
    "inc_badge": {"en": "🏅 Badge: Run Rescuer. You think like an ML engineer, {addr}.",
                  "hi": "🏅 बैज: Run Rescuer। आप ML इंजीनियर की तरह सोचते हैं, {addr}।",
                  "hinglish": "🏅 Badge: Run Rescuer. Aap ML engineer ki tarah sochte ho, {addr}."},
    "inc_keys": {"en": "↑↓ incident   1 2 3 decide   Esc back", "hi": "↑↓ घटना   1 2 3 फ़ैसला   Esc वापस",
                 "hinglish": "↑↓ incident   1 2 3 faisla   Esc wapas"},
})

# (id, when, icon, {lang: (title, situation, [(option, verdict 'good'|'ok'|'bad', feedback) × 3], what we did, lesson)})
INCIDENTS = [
    ("heat", "12 Oct, 01:50", "🌡️", {
        "en": ("The GPU is at 83°C",
               "Training is running at full speed. The GPU reads 83°C, 173 watts, and the laptop's exhaust is throwing very hot "
               "air. 11 hours of training are still left.",
               [("Keep full speed. 83°C is within the chip's limits.", "ok",
                 "It's true the chip protects itself near 87°C, but 11 more hours at the edge stresses the fans and battery. "
                 "Speed isn't everything."),
                ("Stop training until tomorrow night.", "bad",
                 "Safe, but you lose a whole day and miss the release. Overreacting has a cost too."),
                ("Pause 5 minutes to cool down, then add a heat limiter that slows a little when hot.", "good",
                 "Cool now, and prevent it from happening again, at a small, bounded cost.")],
               "A 5-minute freeze, then a limiter: above 77°C, MONA pauses 0.03 s after each 0.18 s of work, never more than "
               "15% slower. The GPU settled around 80°C and the finish moved by about an hour.",
               "Data centres spend almost as much on cooling as on computing. Hardware limits are part of every training plan."),
        "hi": ("GPU 83°C पर है",
               "ट्रेनिंग पूरी रफ़्तार से चल रही है। GPU 83°C, 173 वॉट दिखा रहा है, और लैपटॉप के वेंट से बहुत गर्म हवा निकल रही है। अभी 11 "
               "घंटे की ट्रेनिंग बाकी है।",
               [("पूरी रफ़्तार चलने दो। 83°C चिप की सीमा के अंदर है।", "ok",
                 "सच है कि चिप ~87°C पर ख़ुद को बचाती है, पर 11 घंटे सीमा पर चलना पंखों और बैटरी पर दबाव डालता है। रफ़्तार ही सब कुछ नहीं।"),
                ("कल रात तक ट्रेनिंग रोक दो।", "bad", "सुरक्षित, पर पूरा दिन जाता है और रिलीज़ छूटती है। ज़रूरत से ज़्यादा डरने की भी क़ीमत है।"),
                ("5 मिनट ठंडा होने दो, फिर हीट लिमिटर लगाओ जो गर्म होने पर थोड़ा धीमा करे।", "good",
                 "अभी ठंडक, और आगे के लिए रोकथाम, छोटी और तय क़ीमत पर।")],
               "5 मिनट का ठहराव, फिर लिमिटर: 77°C से ऊपर MONA हर 0.18 सेकंड काम के बाद 0.03 सेकंड रुकती है, कभी 15% से ज़्यादा धीमी नहीं। "
               "GPU लगभग 80°C पर टिका और ट्रेनिंग लगभग एक घंटा आगे खिसकी।",
               "डेटा सेंटर ठंडक पर लगभग उतना ही ख़र्च करते हैं जितना कंप्यूटिंग पर। हार्डवेयर की सीमाएँ हर ट्रेनिंग योजना का हिस्सा हैं।"),
        "hinglish": ("GPU 83°C par hai",
                     "Training full speed par chal rahi hai. GPU 83°C, 173 watts dikha raha hai, aur laptop ke vent se bahut garam hawa nikal "
                     "rahi hai. Abhi 11 ghante ki training baaki hai.",
                     [("Full speed chalne do. 83°C chip ki limit ke andar hai.", "ok",
                       "Sach hai ki chip ~87°C par khud ko bachaati hai, par 11 ghante limit par chalna fans aur battery par pressure daalta "
                       "hai. Speed hi sab kuch nahi."),
                      ("Kal raat tak training rok do.", "bad", "Safe, par poora din jaata hai aur release chhoot-ta hai. Zaroorat se zyada "
                       "darne ki bhi keemat hai."),
                      ("5 minute thanda hone do, phir heat limiter lagao jo garam hone par thoda slow kare.", "good",
                       "Abhi cooling, aur aage ke liye rokthaam, chhoti aur fixed keemat par.")],
                     "5 minute ka freeze, phir limiter: 77°C se upar MONA har 0.18 second kaam ke baad 0.03 second rukti hai, kabhi 15% se "
                     "zyada slow nahi. GPU lagbhag 80°C par tika aur training lagbhag ek ghanta aage khiski.",
                     "Data centres cooling par lagbhag utna hi kharch karte hain jitna computing par. Hardware limits har training plan ka "
                     "hissa hain.")}),
    ("copyright", "12 Oct, 01:00", "⚖️", {
        "en": ("Copyrighted text in the data",
               "0.8 billion tokens in, you learn that the Awadhi data includes a modern Hindi commentary on Tulsidas. The verse "
               "is 450 years old (public domain), but the commentary is probably still under copyright.",
               [("Keep it. It's less than 1% of the data; nobody will notice.", "bad",
                 "Small doesn't mean allowed. You couldn't publish the data or demos honestly, and it breaks trust."),
                ("Stop now, remove the commentary, continue with verse only, and say so in the model card.", "good",
                 "Fixes the problem from here on, costs an hour, and is honest about what happened before."),
                ("Throw everything away and restart training from zero.", "ok",
                 "The cleanest possible fix, but it wastes 10 hours for a tiny share of data. Removing it and disclosing is "
                 "the usual, reasonable step.")],
               "Training was stopped at 0.80B tokens. The commentary was moved out of the project; only 245,710 tokens of verse "
               "remained. The release script now scans everything it publishes for commentary words and refuses to upload "
               "if it finds any. The model card says what happened.",
               "Data licensing is one of the biggest questions in AI today. Labs keep records of every source for this reason."),
        "hi": ("डेटा में कॉपीराइट वाला पाठ",
               "0.8 अरब टोकन के बाद पता चलता है कि अवधी डेटा में तुलसीदास पर एक आधुनिक हिंदी टीका भी है। चौपाइयाँ 450 साल पुरानी हैं (सार्वजनिक), "
               "पर टीका शायद अभी कॉपीराइट में है।",
               [("रहने दो। डेटा का 1% से भी कम है; किसी को पता नहीं चलेगा।", "bad",
                 "छोटा होने का मतलब अनुमति नहीं। आप डेटा या डेमो ईमानदारी से प्रकाशित नहीं कर पाते, और भरोसा टूटता है।"),
                ("अभी रोको, टीका हटाओ, सिर्फ़ चौपाइयों के साथ आगे बढ़ो, और मॉडल कार्ड में बताओ।", "good",
                 "आगे से समस्या ख़त्म, एक घंटा लगता है, और पहले जो हुआ उसके बारे में ईमानदारी।"),
                ("सब फेंककर ट्रेनिंग शून्य से दोबारा शुरू करो।", "ok",
                 "सबसे साफ़ हल, पर डेटा के छोटे से हिस्से के लिए 10 घंटे बर्बाद। हटाकर बता देना आम और समझदार कदम है।")],
               "ट्रेनिंग 0.80 अरब टोकन पर रोकी गई। टीका प्रोजेक्ट से बाहर की गई; सिर्फ़ 2,45,710 टोकन चौपाइयाँ बचीं। रिलीज़ स्क्रिप्ट अब प्रकाशित "
               "होने वाली हर चीज़ में टीका के शब्द खोजती है और मिलने पर अपलोड से मना कर देती है। मॉडल कार्ड में सब लिखा है।",
               "डेटा लाइसेंस आज AI के सबसे बड़े सवालों में से है। इसीलिए लैब हर स्रोत का रिकॉर्ड रखती हैं।"),
        "hinglish": ("Data mein copyrighted text",
                     "0.8 billion tokens ke baad pata chalta hai ki Awadhi data mein Tulsidas par ek modern Hindi commentary bhi hai. Chaupaiyan "
                     "450 saal purani hain (public domain), par commentary shayad abhi copyright mein hai.",
                     [("Rehne do. Data ka 1% se bhi kam hai; kisi ko pata nahi chalega.", "bad",
                       "Chhota hone ka matlab permission nahi. Aap data ya demos imaandaari se publish nahi kar paate, aur trust toot-ta hai."),
                      ("Abhi roko, commentary hatao, sirf chaupaiyon ke saath aage badho, aur model card mein batao.", "good",
                       "Aage se problem khatam, ek ghanta lagta hai, aur pehle jo hua uske baare mein imaandaari."),
                      ("Sab phenk kar training zero se dobara shuru karo.", "ok",
                       "Sabse saaf solution, par data ke chhote se hisse ke liye 10 ghante barbaad. Hatakar bata dena normal aur samajhdaar "
                       "step hai.")],
                     "Training 0.80 billion tokens par roki gayi. Commentary project se bahar ki gayi; sirf 2,45,710 tokens chaupaiyan bachin. "
                     "Release script ab publish hone wali har cheez mein commentary ke words dhoondhti hai aur milne par upload se mana kar deti "
                     "hai. Model card mein sab likha hai.",
                     "Data licensing aaj AI ke sabse bade sawaalon mein se hai. Isiliye labs har source ka record rakhti hain.")}),
    ("watchdog", "11 Oct, 20:10", "🐕", {
        "en": ("The watchdog cries wolf",
               "Minutes after the big run starts, the watchdog reports 'training dead!' and restarts it. Then again. And again. "
               "But the GPU is busy at 99%.",
               [("Turn the watchdog off. It's broken.", "bad",
                 "Then nobody restarts training if it really crashes at 3 AM. You'd lose the protection you need most."),
                ("Find out why it can't see the training, and fix that.", "good",
                 "A false alarm is a bug with a cause. Fix the cause and keep the guard."),
                ("Ignore it. After 3 restarts it gives up by itself.", "ok",
                 "Its safety limit did work, but then it's not guarding anything for the rest of the night.")],
               "The cause: training ran as a hidden 'pythonw.exe' process, and the watchdog only looked for 'python.exe'. One "
               "line fixed it. Its built-in limit (max 3 restarts in 3 hours, then stop and alert) stopped the false alarms "
               "from causing real damage.",
               "Monitoring that raises false alarms gets ignored, and then a real alarm is missed. Every automatic action "
               "needs a limit."),
        "hi": ("वॉचडॉग का झूठा अलार्म",
               "बड़ी ट्रेनिंग शुरू होने के कुछ मिनट बाद वॉचडॉग कहता है 'ट्रेनिंग रुक गई!' और उसे दोबारा शुरू करता है। फिर से। और फिर से। "
               "पर GPU 99% व्यस्त है।",
               [("वॉचडॉग बंद करो। वह टूटा है।", "bad",
                 "फिर सुबह 3 बजे सच में क्रैश हुआ तो कोई ट्रेनिंग दोबारा शुरू नहीं करेगा। सबसे ज़रूरी सुरक्षा ही चली जाएगी।"),
                ("पता करो कि वह ट्रेनिंग को देख क्यों नहीं पा रहा, और उसे ठीक करो।", "good",
                 "झूठा अलार्म भी एक बग है जिसकी वजह होती है। वजह ठीक करो और गार्ड रखो।"),
                ("अनदेखा करो। 3 बार के बाद वह ख़ुद रुक जाता है।", "ok",
                 "उसकी सुरक्षा-सीमा ने काम किया, पर फिर बाकी रात वह किसी चीज़ की रखवाली नहीं करता।")],
               "वजह: ट्रेनिंग छिपी 'pythonw.exe' प्रक्रिया के रूप में चल रही थी, और वॉचडॉग सिर्फ़ 'python.exe' खोज रहा था। एक लाइन से ठीक हुआ। "
               "उसकी अपनी सीमा (3 घंटे में ज़्यादा से ज़्यादा 3 बार, फिर रुककर चेतावनी) ने झूठे अलार्म को असली नुक़सान करने से रोका।",
               "जो निगरानी झूठे अलार्म देती है उसे लोग अनदेखा करने लगते हैं, और फिर असली अलार्म छूट जाता है। हर अपने-आप होने वाले काम की "
               "सीमा होनी चाहिए।"),
        "hinglish": ("Watchdog ka false alarm",
                     "Badi training shuru hone ke kuch minute baad watchdog kehta hai 'training ruk gayi!' aur use restart karta hai. Phir se. "
                     "Aur phir se. Par GPU 99% busy hai.",
                     [("Watchdog band karo. Woh toota hai.", "bad",
                       "Phir subah 3 baje sach mein crash hua to koi training restart nahi karega. Sabse zaroori protection hi chali jaayegi."),
                      ("Pata karo ki woh training ko dekh kyun nahi pa raha, aur use theek karo.", "good",
                       "False alarm bhi ek bug hai jiski wajah hoti hai. Wajah theek karo aur guard rakho."),
                      ("Ignore karo. 3 baar ke baad woh khud ruk jaata hai.", "ok",
                       "Uski safety limit ne kaam kiya, par phir baaki raat woh kisi cheez ki rakhwali nahi karta.")],
                     "Wajah: training chhupi 'pythonw.exe' process ke roop mein chal rahi thi, aur watchdog sirf 'python.exe' dhoondh raha tha. "
                     "Ek line se theek hua. Uski apni limit (3 ghante mein max 3 restarts, phir rukkar alert) ne false alarm ko asli nuksaan "
                     "karne se roka.",
                     "Jo monitoring false alarms deti hai use log ignore karne lagte hain, aur phir asli alarm chhoot jaata hai. Har automatic "
                     "kaam ki limit honi chahiye.")}),
    ("charger", "12 Oct, 07:10", "🔌", {
        "en": ("The charger slips out",
               "Early morning, nobody awake. The laptop suddenly switches to battery while training is using 170 watts.",
               [("Keep training on battery. It'll come back.", "bad",
                 "The battery drains in minutes at this power. If the laptop dies while saving a checkpoint, the save can be "
                 "corrupted and hours are lost."),
                ("Freeze training instantly in memory, and continue the moment power returns.", "good",
                 "Nothing is lost, nothing is written halfway, and no human needs to be awake."),
                ("Save a checkpoint and shut everything down.", "ok",
                 "Safe, but then someone must restart it by hand, and the night is wasted if nobody is awake.")],
               "The power guard froze the training process in place within seconds, twice (07:10 and 07:29), and resumed it "
               "when power returned. Not a single step was lost.",
               "Big clusters lose power, network and GPUs all the time. Good systems expect failure and recover automatically."),
        "hi": ("चार्जर निकल गया",
               "सुबह-सुबह, कोई जागा नहीं। ट्रेनिंग 170 वॉट खा रही है और लैपटॉप अचानक बैटरी पर चला जाता है।",
               [("बैटरी पर ट्रेनिंग चलने दो। बिजली लौट आएगी।", "bad",
                 "इतनी खपत पर बैटरी मिनटों में ख़त्म होती है। चेकपॉइंट सहेजते समय लैपटॉप बंद हुआ तो फ़ाइल ख़राब हो सकती है और घंटों का काम जाता है।"),
                ("ट्रेनिंग को तुरंत मेमोरी में ही रोक दो, और बिजली लौटते ही आगे बढ़ाओ।", "good",
                 "कुछ नहीं खोता, कुछ भी आधा नहीं लिखा जाता, और किसी इंसान को जागना नहीं पड़ता।"),
                ("चेकपॉइंट सहेजो और सब बंद कर दो।", "ok",
                 "सुरक्षित, पर फिर किसी को हाथ से दोबारा शुरू करना पड़ेगा, और कोई जागा न हो तो रात बेकार।")],
               "पावर गार्ड ने दोनों बार (07:10 और 07:29) कुछ सेकंड में ट्रेनिंग प्रक्रिया को वहीं रोका, और बिजली लौटने पर फिर चालू किया। एक भी "
               "कदम नहीं खोया।",
               "बड़े क्लस्टर में बिजली, नेटवर्क और GPU बार-बार फ़ेल होते हैं। अच्छे सिस्टम ख़राबी की उम्मीद रखते हैं और अपने-आप सँभलते हैं।"),
        "hinglish": ("Charger nikal gaya",
                     "Subah-subah, koi jaaga nahi. Training 170 watts kha rahi hai aur laptop achanak battery par chala jaata hai.",
                     [("Battery par training chalne do. Power laut aayegi.", "bad",
                       "Itni khapat par battery minutes mein khatam hoti hai. Checkpoint save karte waqt laptop band hua to file kharab ho sakti "
                       "hai aur ghanton ka kaam jaata hai."),
                      ("Training ko turant memory mein hi freeze karo, aur power lautte hi aage badhao.", "good",
                       "Kuch nahi khota, kuch bhi aadha nahi likha jaata, aur kisi insaan ko jaagna nahi padta."),
                      ("Checkpoint save karo aur sab band kar do.", "ok",
                       "Safe, par phir kisi ko haath se restart karna padega, aur koi jaaga na ho to raat bekaar.")],
                     "Power guard ne dono baar (07:10 aur 07:29) kuch seconds mein training process ko wahin freeze kiya, aur power lautne par "
                     "phir chalu kiya. Ek bhi step nahi khoya.",
                     "Bade clusters mein power, network aur GPUs baar-baar fail hote hain. Achhe systems failure expect karte hain aur apne-aap "
                     "sambhalte hain.")}),
    ("hinglish", "11 Oct", "🔤", {
        "en": ("The Hinglish looks machine-made",
               "Reading samples of the Hinglish data, the team finds odd spellings no real person types, because the text was "
               "made by a machine (transliterated from Hindi).",
               [("Use it as it is. A model can cope.", "bad",
                 "A model learns exactly what it reads. Feed it odd spellings and it writes odd spellings."),
                ("Drop Hinglish completely.", "ok",
                 "Clean, but you lose a language millions of people actually type every day."),
                ("Fix the most common bad spellings with rules, and keep Hinglish as a small share of the mix.", "good",
                 "Improves quality cheaply and keeps the language. Perfect data doesn't exist; good-enough data does.")],
               "About 70 frequent words were mapped to the way people really type them, and Hinglish was kept at 5% of the "
               "mix. You can see the fixes in the Data stage.",
               "Synthetic (machine-made) data is now everywhere in AI. Checking it by eye, sample by sample, still catches "
               "problems no metric shows."),
        "hi": ("हिंग्लिश मशीन से बनी लगती है",
               "हिंग्लिश डेटा के नमूने पढ़ने पर टीम को अजीब वर्तनियाँ दिखती हैं जो कोई असली इंसान नहीं लिखता, क्योंकि पाठ मशीन ने बनाया था "
               "(हिंदी से लिप्यंतरण)।",
               [("जैसा है वैसा इस्तेमाल करो। मॉडल सँभाल लेगा।", "bad", "मॉडल वही सीखता है जो पढ़ता है। अजीब वर्तनी खिलाओगे तो अजीब वर्तनी लिखेगा।"),
                ("हिंग्लिश पूरी तरह हटा दो।", "ok", "साफ़, पर वह भाषा खो जाती है जो करोड़ों लोग रोज़ टाइप करते हैं।"),
                ("सबसे आम ग़लत वर्तनियाँ नियमों से सुधारो, और हिंग्लिश को मिश्रण का छोटा हिस्सा रखो।", "good",
                 "सस्ते में गुणवत्ता सुधरती है और भाषा बची रहती है। सही डेटा होता ही नहीं; काफ़ी अच्छा डेटा होता है।")],
               "लगभग 70 आम शब्दों को उस तरह बदला गया जैसे लोग सच में लिखते हैं, और हिंग्लिश को मिश्रण का 5% रखा गया। सुधार आप डेटा चरण में "
               "देख सकते हैं।",
               "सिंथेटिक (मशीन से बना) डेटा आज AI में हर जगह है। उसे आँख से, नमूना-दर-नमूना जाँचना अब भी वे समस्याएँ पकड़ता है जो कोई अंक नहीं "
               "दिखाता।"),
        "hinglish": ("Hinglish machine-made lagti hai",
                     "Hinglish data ke samples padhne par team ko ajeeb spellings dikhti hain jo koi asli insaan nahi likhta, kyunki text machine "
                     "ne banaya tha (Hindi se transliterate).",
                     [("Jaisa hai waisa use karo. Model sambhal lega.", "bad",
                       "Model wahi seekhta hai jo padhta hai. Ajeeb spellings khilaoge to ajeeb spellings likhega."),
                      ("Hinglish poori tarah hata do.", "ok", "Saaf, par woh language kho jaati hai jo crore-on log roz type karte hain."),
                      ("Sabse common galat spellings rules se theek karo, aur Hinglish ko mix ka chhota hissa rakho.", "good",
                       "Saste mein quality sudharti hai aur language bachi rehti hai. Perfect data hota hi nahi; good-enough data hota hai.")],
                     "Lagbhag 70 common words ko us tarah badla gaya jaise log sach mein likhte hain, aur Hinglish ko mix ka 5% rakha gaya. "
                     "Fixes aap Data stage mein dekh sakte ho.",
                     "Synthetic (machine-made) data aaj AI mein har jagah hai. Use aankh se, sample-by-sample check karna ab bhi woh problems "
                     "pakadta hai jo koi metric nahi dikhata.")}),
    ("download", "11 Oct", "📥", {
        "en": ("Downloads stuck at 0%",
               "Gigabytes of training data need downloading before tonight's run. The default download tool keeps stalling: "
               "progress frozen, no error.",
               [("Keep waiting. It'll start eventually.", "bad", "Hope is not a plan. Tonight's run would start without data."),
                ("Switch to a simple download method that can resume where it stopped.", "good",
                 "When a fancy tool fails, a boring reliable one usually works. Resuming means no restart from zero."),
                ("Pick a different, smaller dataset that downloads quickly.", "ok",
                 "It works, but you'd change your data plan because of a tool problem.")],
               "We switched from the stalling protocol to plain HTTP downloads with resume (curl -C -). Everything arrived in "
               "about two hours. Uploads use the same lesson.",
               "At big labs, moving data is a whole engineering job. The boring parts decide whether the exciting parts happen."),
        "hi": ("डाउनलोड 0% पर अटके",
               "आज रात की ट्रेनिंग से पहले गीगाबाइट डेटा डाउनलोड होना है। सामान्य डाउनलोड टूल बार-बार अटक जाता है: प्रगति रुकी, कोई ग़लती "
               "नहीं दिखती।",
               [("इंतज़ार करते रहो। कभी तो शुरू होगा।", "bad", "उम्मीद योजना नहीं है। आज रात की ट्रेनिंग बिना डेटा के शुरू होगी।"),
                ("ऐसे सीधे-सादे डाउनलोड तरीक़े पर जाओ जो रुकने के बाद वहीं से आगे बढ़ सके।", "good",
                 "जब फ़ैंसी टूल फ़ेल हो, तो सीधा-सादा भरोसेमंद तरीक़ा अक्सर चलता है। आगे बढ़ने का मतलब शून्य से दोबारा नहीं।"),
                ("कोई दूसरा, छोटा डेटासेट चुन लो जो जल्दी आ जाए।", "ok", "काम चल जाएगा, पर एक टूल की वजह से आप अपनी डेटा योजना बदल देंगे।")],
               "हम अटकने वाले प्रोटोकॉल से हटकर सीधे HTTP डाउनलोड पर गए जो रुकने के बाद आगे बढ़ सके (curl -C -)। सब लगभग दो घंटे में आ गया। "
               "अपलोड में भी यही सबक़ इस्तेमाल हुआ।",
               "बड़ी लैब में डेटा इधर-उधर ले जाना अपने-आप में एक पूरा इंजीनियरिंग काम है। उबाऊ हिस्से तय करते हैं कि रोमांचक हिस्से हो पाएँगे या नहीं।"),
        "hinglish": ("Downloads 0% par atke",
                     "Aaj raat ki training se pehle gigabytes data download hona hai. Default download tool baar-baar atak jaata hai: progress "
                     "ruki, koi error nahi.",
                     [("Wait karte raho. Kabhi to shuru hoga.", "bad", "Ummeed plan nahi hai. Aaj raat ki training bina data ke shuru hogi."),
                      ("Simple download method par jao jo rukne ke baad wahin se resume ho sake.", "good",
                       "Jab fancy tool fail ho, to boring reliable tareeka aksar chalta hai. Resume ka matlab zero se dobara nahi."),
                      ("Koi doosra, chhota dataset chun lo jo jaldi aa jaaye.", "ok",
                       "Kaam chal jaayega, par ek tool ki wajah se aap apna data plan badal doge.")],
                     "Hum atakne wale protocol se hatkar plain HTTP downloads par gaye jo resume ho sakein (curl -C -). Sab lagbhag do ghante "
                     "mein aa gaya. Uploads mein bhi yahi sabak use hua.",
                     "Badi labs mein data idhar-udhar le jaana apne aap mein poora engineering kaam hai. Boring hisse decide karte hain ki "
                     "exciting hisse ho paayenge ya nahi.")}),
]


class IncidentScreen(Screen):
    BINDINGS = [Binding("escape", "app.pop_screen", "back"), Binding("1", "decide(0)", show=False),
                Binding("2", "decide(1)", show=False), Binding("3", "decide(2)", show=False)]

    def compose(self) -> ComposeResult:
        with Horizontal(classes="lab-head"):
            yield Avatar(id="avatar", classes="lab-avatar")
            yield Static(id="title", classes="lab-title")
        yield Static(id="explain", classes="explain")
        with Horizontal(id="tour-cols"):
            yield OptionList(id="incidents")
            with VerticalScroll(id="tour-right"):
                yield Static(id="case", classes="panel")
        yield Static(id="keys", classes="keys")

    def on_mount(self):
        self.answers = {}                                  # incident id -> chosen option index
        self.refresh_texts()
        box = self.query_one("#incidents", OptionList)
        box.highlighted = 0
        box.focus()

    def refresh_texts(self):
        app, tr = self.app, self.app.tr
        self.query_one("#title", Static).update(tr("inc_title"))
        self.query_one("#explain", Static).update(tr("inc_explain"))
        self.query_one("#keys", Static).update(tr("inc_keys"))
        self.fill()

    def fill(self):
        app = self.app
        box = self.query_one("#incidents", OptionList)
        keep = box.highlighted
        box.clear_options()
        for iid, when, icon, d in INCIDENTS:
            title = d[app.state.lang][0]
            mark = ""
            if iid in self.answers:
                mark = {"good": " ✅", "ok": " 🤔", "bad": " ⚠️"}[d["en"][2][self.answers[iid]][1]]
            box.add_option(Option(f" {icon} {app.roman(title) if app.state.romanize else title}{mark}", id=iid))
        box.highlighted = keep if keep is not None else 0
        self.show()

    def on_option_list_option_highlighted(self, event):
        self.show()

    def current(self):
        return INCIDENTS[self.query_one("#incidents", OptionList).highlighted or 0]

    def action_decide(self, i: int):
        iid = self.current()[0]
        if iid not in self.answers:
            self.answers[iid] = i
            self.fill()

    def show(self):
        app, tr = self.app, self.app.tr
        iid, when, icon, d = self.current()
        title, situation, options, did, lesson = d[app.state.lang]
        out = Text(f"{icon} {title}", style="bold #f9e2af")
        out.append(f"    {when}\n\n", style="#9399b2")
        out.append(situation + "\n\n", style="#cdd6f4")
        chosen = self.answers.get(iid)
        for n, (text, verdict, feedback) in enumerate(options):
            style = "bold #cdd6f4" if chosen is None else ("bold #a6e3a1" if verdict == "good" else "#9399b2")
            out.append(f"  {n + 1}. {text}\n", style=style)
        out.append("\n")
        if chosen is None:
            out.append(tr("inc_choose"), style="bold #f9e2af")
        else:
            verdict, feedback = options[chosen][1], options[chosen][2]
            out.append(tr({"good": "inc_good", "ok": "inc_ok", "bad": "inc_bad"}[verdict]) + " ",
                       style="bold #a6e3a1" if verdict == "good" else "bold #f5c2e7")
            out.append(feedback + "\n\n", style="#cdd6f4")
            out.append(tr("inc_real") + "\n", style="bold #89dceb")
            out.append(did + "\n\n", style="#cdd6f4")
            out.append(tr("inc_lesson") + "\n", style="bold #cba6f7")
            out.append(lesson + "\n\n", style="italic #bac2de")
            good = sum(1 for k, v in self.answers.items()
                       if next(x for x in INCIDENTS if x[0] == k)[3]["en"][2][v][1] == "good")
            out.append(tr("inc_score", a=good, b=len(self.answers)), style="bold #f9e2af")
            if len(self.answers) == len(INCIDENTS):
                app.state.complete("incidents", badge="Run Rescuer" if good >= 5 else None)
                if good >= 5:
                    out.append("\n" + tr("inc_badge"), style="bold #f9e2af")
        self.query_one("#case", Static).update(app.roman(out.plain) if app.state.romanize else out)

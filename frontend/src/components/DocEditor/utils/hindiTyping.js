import Sanscript from "@sanskrit-coders/sanscript"

/**
 * Hindi (Devanagari) transliteration for the document editor.
 *
 * Typing a Roman word followed by a word boundary (space, punctuation, Enter)
 * converts it to Devanagari, Google-Input-Tools style. Pure ITRANS cannot
 * spell common Hindi words correctly from naive lowercase input
 * ("sarkar" would become सर्कर् instead of सरकार), so frequent
 * administrative words are mapped explicitly and everything else falls back
 * to ITRANS. Digits are never converted (official documents keep 0-9).
 */

// Frequent administrative vocabulary: correct spellings that a
// deterministic scheme cannot derive from lowercase input.
const COMMON_WORDS = {
	aades: "आदेश",
	aadesh: "आदेश",
	aagya: "आज्ञा",
	aaj: "आज",
	aavedan: "आवेदन",
	adhikari: "अधिकारी",
	adhyaksh: "अध्यक्ष",
	anumati: "अनुमति",
	arop: "आरोप",
	avkash: "अवकाश",
	baithak: "बैठक",
	bayan: "बयान",
	bhatta: "भत्ता",
	bijli: "बिजली",
	chhutti: "छुट्टी",
	chikitsalaya: "चिकित्सालय",
	dand: "दण्ड",
	desh: "देश",
	din: "दिन",
	dinank: "दिनांक",
	gawah: "गवाह",
	ghoshna: "घोषणा",
	gyapan: "ज्ञापन",
	hastakshar: "हस्ताक्षर",
	hindi: "हिन्दी",
	jaanch: "जांच",
	jila: "जिला",
	jiladhikari: "जिलाधिकारी",
	jurmana: "जुर्माना",
	kal: "कल",
	karyakram: "कार्यक्रम",
	karyalaya: "कार्यालय",
	karyalay: "कार्यालय",
	karyavahi: "कार्यवाही",
	khatoni: "खतौनी",
	khatauni: "खतौनी",
	khet: "खेत",
	kisan: "किसान",
	kramank: "क्रमांक",
	lekhpal: "लेखपाल",
	mahina: "महीना",
	mahoday: "महोदय",
	mahodaya: "महोदया",
	mohar: "मोहर",
	muavza: "मुआवज़ा",
	naam: "नाम",
	naksha: "नक्शा",
	nideshak: "निदेशक",
	nirdesh: "निर्देश",
	nirman: "निर्माण",
	nivedan: "निवेदन",
	niyukti: "नियुक्ति",
	nyayadhish: "न्यायाधीश",
	nyayalaya: "न्यायालय",
	padonnati: "पदोन्नति",
	pani: "पानी",
	paripatra: "परिपत्र",
	pata: "पता",
	patra: "पत्र",
	patrank: "पत्रांक",
	police: "पुलिस",
	pradesh: "प्रदेश",
	praman: "प्रमाण",
	prarthana: "प्रार्थना",
	prapatra: "प्रपत्र",
	prastav: "प्रस्ताव",
	rajasva: "राजस्व",
	rajya: "राज्य",
	sachiv: "सचिव",
	sadak: "सड़क",
	saal: "साल",
	samay: "समय",
	sankhya: "संख्या",
	sarkar: "सरकार",
	sarkari: "सरकारी",
	seema: "सीमा",
	shapath: "शपथ",
	shapathpatra: "शपथपत्र",
	shikayat: "शिकायत",
	shiksha: "शिक्षा",
	shubharambh: "शुभारम्भ",
	sthan: "स्थान",
	sthanantaran: "स्थानांतरण",
	suchi: "सूची",
	samiti: "समिति",
	samjhauta: "समझौता",
	saptah: "सप्ताह",
	sveekriti: "स्वीकृति",
	swasthya: "स्वास्थ्य",
	tahsil: "तहसील",
	tehsil: "तहसील",
	tehsildar: "तहसीलदार",
	thana: "थाना",
	uttarakhand: "उत्तराखण्ड",
	uttrakhand: "उत्तराखण्ड",
	vadi: "वादी",
	prativadi: "प्रतिवादी",
	vetan: "वेतन",
	vibhaag: "विभाग",
	vibhag: "विभाग",
	vidyalaya: "विद्यालय",
	vigyapan: "विज्ञापन",
	vigyapti: "विज्ञप्ति",
	vikas: "विकास",
	vishay: "विषय",
	vivad: "विवाद",
	vivaran: "विवरण",
	yojana: "योजना",
	zameen: "ज़मीन",
}

// Characters that end a word: typing one converts the Roman word before it.
const BOUNDARY_CHARS = new Set([
	" ",
	" ",
	".",
	",",
	"?",
	"!",
	";",
	":",
	"।",
	"-",
	"–",
	"—",
	"(",
	")",
	'"',
	"'",
])

export function isBoundaryChar(ch) {
	return typeof ch === "string" && ch.length === 1 && BOUNDARY_CHARS.has(ch)
}

export function romanToDevanagari(word) {
	if (!word || !/^[A-Za-z]+$/.test(word)) return word
	const known = COMMON_WORDS[word.toLowerCase()]
	if (known) return known
	// ITRANS fallback; a trailing halant is almost never wanted in Hindi prose.
	return Sanscript.t(word, "itrans", "devanagari").replace(/्$/, "")
}

/**
 * Convert the Roman word immediately before the cursor to Devanagari.
 * Returns true when a replacement was dispatched.
 */
export function convertWordBeforeCursor(view) {
	const { state } = view
	const { $from } = state.selection
	if (!state.selection.empty) return false
	if ($from.parent.type.name === "codeBlock") return false
	const textBefore = $from.parent.textBetween(0, $from.parentOffset, null, "￼")
	const match = textBefore.match(/[A-Za-z]+$/)
	if (!match) return false
	const converted = romanToDevanagari(match[0])
	if (!converted || converted === match[0]) return false
	view.dispatch(state.tr.insertText(converted, $from.pos - match[0].length, $from.pos))
	return true
}

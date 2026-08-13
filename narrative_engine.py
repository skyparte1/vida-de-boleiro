"""Infraestrutura declarativa para acontecimentos narrativos persistentes.

As definições abaixo não decidem o fluxo da carreira: elas apenas informam
quando um evento pode existir e quais efeitos seguros uma decisão produz.
"""

from __future__ import annotations

from copy import deepcopy
from datetime import date, timedelta
import random

from career_lifecycle import apply_terminal_effect
from competition_engine import competition_context
from database import get_club
from feedback_engine import contextual_text
from narrative_catalog import EXPANDED_NARRATIVE_EVENTS


REPUTATION_KEYS = (
    "locker_room", "fans", "media", "discipline", "controversy", "leadership",
)
BEHAVIOR_KEYS = (
    "authoritarian_choices", "media_conflicts", "locker_room_conflicts", "gambling_incidents",
)
PLAYER_EFFECT_KEYS = {"morale", "form", "fatigue", "overall", "weak_foot"}
RARITY_WEIGHTS = {"common": 100, "uncommon": 45, "rare": 15, "very_rare": 4, "legendary": 1}


NARRATIVE_EVENTS = {
    "locker_room_fight": {
        "key": "locker_room_fight", "type": "dressing_room", "title": "Briga no vestiário",
        "text": "Uma discussão com um companheiro de equipe saiu do controle após o treino.",
        "cooldown": 24,
        "conditions": {"min_age": 16, "status": "active"},
        "choices": [
            {"id": "apologize", "label": "Pedir desculpas", "outcomes": [{"weight": 80, "result_title": "Tentativa de reconciliação", "result_text": "Você procura seu companheiro depois da discussão e pede desculpas. Ele aceita o gesto, e o clima começa a melhorar.", "effects": {"reputation": {"locker_room": 7, "discipline": 4, "leadership": 1}, "player": {"morale": 2}}}, {"weight": 20, "result_title": "Desculpas mal recebidas", "result_text": "Você tenta encerrar a discussão, mas seu companheiro não parece disposto a esquecer o ocorrido. A tensão diminui pouco.", "effects": {"reputation": {"locker_room": 2}, "player": {"morale": -2}, "set_flags": ["locker_room_conflict_unresolved"]}}]},
            {"id": "blame_teammate", "label": "Culpar o companheiro", "outcomes": [{"weight": 65, "result_title": "Clima ainda mais pesado", "result_text": "Sua tentativa de jogar a culpa no companheiro gera novas discussões e aumenta a tensão dentro do elenco.", "effects": {"reputation": {"locker_room": -10, "controversy": 8, "discipline": -3}, "behavior": {"locker_room_conflicts": 1}, "set_flags": ["public_locker_room_conflict"], "follow_ups": [{"event_key": "locker_room_backlash", "after_weeks": 3}], "history": "Você culpou o companheiro pela discussão no vestiário."}}, {"weight": 25, "result_title": "Sua versão ganha força", "result_text": "Você coloca a responsabilidade sobre o companheiro, e parte do elenco parece acreditar na sua versão.", "effects": {"reputation": {"locker_room": -4, "leadership": 3, "controversy": 5}, "behavior": {"locker_room_conflicts": 1}}}, {"weight": 10, "result_title": "A comissão intervém", "result_text": "A situação passa dos limites e chega à comissão técnica, que não fica nada satisfeita com sua postura.", "effects": {"reputation": {"locker_room": -10, "controversy": 8, "discipline": -3}, "behavior": {"locker_room_conflicts": 1}, "set_flags": ["public_locker_room_conflict"], "follow_ups": [{"event_key": "locker_room_backlash", "after_weeks": 3}], "status_momentum": -2, "player": {"morale": -3}}}]},
            {"id": "threaten", "label": "Ameaçar resolver fora do clube", "outcomes": [{"weight": 60, "text": "Sua ameaça piorou o ambiente do grupo.", "effects": {"reputation": {"locker_room": -8, "controversy": 6, "discipline": -7, "leadership": 5}, "behavior": {"locker_room_conflicts": 1, "authoritarian_choices": 1}, "set_flags": ["public_locker_room_conflict"], "follow_ups": [{"event_key": "locker_room_backlash", "after_weeks": 2}]}}, {"weight": 30, "text": "O elenco se intimidou com sua postura.", "effects": {"reputation": {"leadership": 6, "locker_room": -10, "controversy": 6}, "behavior": {"authoritarian_choices": 1}}}, {"weight": 10, "text": "A comissão técnica precisou intervir.", "effects": {"reputation": {"discipline": -10}, "status_momentum": -4, "player": {"morale": -4}, "follow_ups": [{"event_key": "locker_room_backlash", "after_weeks": 2}]}}]},
        ],
    },
    "locker_room_backlash": {
        "key": "locker_room_backlash", "type": "dressing_room", "title": "O elenco reage",
        "text": "Parte do elenco se incomodou com a forma como você conduziu a discussão recente.",
        "unique": True,
        "conditions": {"required_flags": ["public_locker_room_conflict"], "status": "active"},
        "choices": [
            {"id": "reconcile", "label": "Reunir o grupo e conciliar", "effects": {"reputation": {"locker_room": 5, "leadership": 2}, "history": "Você reuniu o elenco para tentar reconstruir o ambiente."}},
            {"id": "double_down", "label": "Manter a posição", "effects": {"reputation": {"locker_room": -7, "controversy": 4, "leadership": 4}, "behavior": {"authoritarian_choices": 1}, "history": "Você manteve a posição diante da reação do elenco."}},
        ],
    },
    "reporter_argument": {
        "key": "reporter_argument", "type": "media", "title": "Pergunta incômoda na coletiva",
        "text": "Um repórter insiste em uma pergunta que você considera desrespeitosa.",
        "cooldown": 20,
        "conditions": {"min_age": 17, "status": "active"},
        "choices": [
            {"id": "answer_calmly", "label": "Responder com calma", "effects": {"reputation": {"media": 5, "discipline": 2}, "history": "Você respondeu à pergunta difícil sem perder a calma."}},
            {"id": "attack_reporter", "label": "Confrontar o repórter", "effects": {"reputation": {"media": -9, "controversy": 8, "discipline": -4}, "behavior": {"media_conflicts": 1}, "set_flags": ["reporter_conflict"], "follow_ups": [{"event_key": "reporter_aftermath", "after_weeks": 4}], "history": "Você discutiu com um repórter durante a coletiva."}},
        ],
    },
    "hair_change": {
        "key": "hair_change", "type": "personal_life", "title": "Visual novo",
        "text": "Você pensa em mudar o visual antes da próxima sequência de jogos.",
        "cooldown": 16,
        "conditions": {"min_age": 16, "status": "active"},
        "choices": [
            {"id": "change_style", "label": "Pintar o cabelo", "outcomes": [{"weight": 70, "result_title": "Novo visual", "result_text": "Você muda o visual e gosta do resultado. A novidade chama alguma atenção, mas sua rotina segue normalmente.", "effects": {"reputation": {"fans": 2, "media": 1}}}, {"weight": 20, "result_title": "Autoestima renovada", "result_text": "A mudança fica ainda melhor do que você esperava. Você chega aos próximos compromissos mais confiante e motivado.", "summary": ["Moral +8", "Desenvolvimento +3"], "effects": {"player": {"morale": 8}, "development_points": 3}}, {"weight": 10, "result_title": "Mudança desastrosa", "result_text": "O procedimento não sai como planejado e causa um corte químico. O resultado abala sua confiança e afeta seu momento fora de campo.", "summary": ["Overall -1", "Moral -10", "Forma -4"], "effects": {"player": {"overall": -1, "morale": -10, "form": -4}, "history": "Um corte químico atrapalhou sua preparação."}}]},
            {"id": "keep_style", "label": "Manter o visual", "outcomes": [{"weight": 100, "result_title": "Visual mantido", "result_text": "Você pensa melhor e decide deixar o cabelo como está. Nada muda na sua rotina.", "effects": {}}]},
        ],
    },
    "gambling_spending": {
        "key": "gambling_spending", "type": "personal_life", "title": "Noite de apostas",
        "text": "Uma noite de apostas chamou a atenção de pessoas próximas ao clube.",
        "cooldown": 26,
        "conditions": {"min_age": 18, "status": "active"},
        "choices": [
            {"id": "stop_early", "label": "Encerrar a noite", "outcomes": [{"weight": 85, "text": "Você encerrou a noite antes que ela virasse um problema.", "effects": {"reputation": {"discipline": 2}}}, {"weight": 15, "text": "Você saiu frustrado, mas evitou uma situação pior.", "effects": {"player": {"morale": -1}}}]},
            {"id": "keep_gambling", "label": "Continuar apostando", "outcomes": [{"weight": 55, "text": "Você perdeu uma parte relevante do dinheiro.", "effects": {"reputation": {"discipline": -6, "controversy": 5}, "behavior": {"gambling_incidents": 1}, "set_flags": ["gambling_attention"], "follow_ups": [{"event_key": "gambling_all_salary", "after_weeks": 6}], "player": {"morale": -3}}}, {"weight": 25, "text": "Você ganhou dinheiro, o que tornou a decisão ainda mais perigosa.", "effects": {"reputation": {"discipline": -4}, "behavior": {"gambling_incidents": 1}, "set_flags": ["gambling_attention"], "follow_ups": [{"event_key": "gambling_all_salary", "after_weeks": 6}], "player": {"morale": 6}}}, {"weight": 15, "text": "A perda foi muito maior do que você esperava.", "effects": {"reputation": {"discipline": -8, "controversy": 6}, "behavior": {"gambling_incidents": 1}, "player": {"morale": -8}}}, {"weight": 5, "text": "Um grande ganho reforçou um comportamento perigoso.", "effects": {"reputation": {"discipline": -6}, "behavior": {"gambling_incidents": 2}, "set_flags": ["gambling_attention"], "follow_ups": [{"event_key": "gambling_all_salary", "after_weeks": 6}], "player": {"morale": 10}}}]},
        ],
    },
    "locker_room_authority": {
        "key": "locker_room_authority", "type": "dressing_room", "title": "Quem manda aqui?",
        "text": "Em um treino tenso, o grupo espera que alguém assuma o comando.",
        "cooldown": 18,
        "conditions": {"min_age": 17, "min_reputation": {"leadership": 8}, "status": "active"},
        "choices": [
            {"id": "impose_authority", "label": "Impor sua autoridade", "effects": {"reputation": {"leadership": 5, "locker_room": -6, "controversy": 4}, "behavior": {"authoritarian_choices": 1}, "history": "Você assumiu uma postura autoritária diante do elenco."}},
            {"id": "listen_first", "label": "Ouvir o grupo primeiro", "effects": {"reputation": {"leadership": 3, "locker_room": 4}, "history": "Você ouviu o grupo antes de orientar o vestiário."}},
        ],
    },
}

NARRATIVE_EVENTS.update(EXPANDED_NARRATIVE_EVENTS)
for _event in NARRATIVE_EVENTS.values():
    _event.setdefault("rarity", "uncommon")
NARRATIVE_EVENTS["locker_room_fight"]["rarity"] = "rare"
NARRATIVE_EVENTS["locker_room_backlash"]["rarity"] = "rare"
NARRATIVE_EVENTS["hair_change"]["rarity"] = "common"
NARRATIVE_EVENTS["reporter_argument"]["rarity"] = "rare"
NARRATIVE_EVENTS["gambling_spending"]["rarity"] = "uncommon"
NARRATIVE_EVENTS["locker_room_authority"]["rarity"] = "uncommon"


def _ensure_contextual_result_fields():
    """Compatibiliza o catálogo legado sem alterar seus outcomes ou efeitos."""
    for event in NARRATIVE_EVENTS.values():
        for choice in event.get("choices", []):
            choice.setdefault("result_title", event["title"])
            choice.setdefault("result_text", event["text"])
            for outcome in choice.get("outcomes", []):
                outcome.setdefault("result_title", choice["result_title"])
                outcome.setdefault("result_text", outcome.get("text") or choice["result_text"])


_ensure_contextual_result_fields()

_CHOICE_RESULT_COPY = {
    ("tattoo", "cancel"): ("Você mudou de ideia", "Depois de pensar melhor, você decide não fazer a tatuagem."),
    ("tattoo", "small"): ("Nova tatuagem", "Você escolhe algo discreto e fica satisfeito com o resultado."),
    ("tattoo", "bold"): ("Visual marcante", "A tatuagem chama bastante atenção e rapidamente vira assunto entre torcedores e imprensa."),
    ("rookie_arrival", "ignore"): ("Cada um por si", "Você decide não se envolver e deixa o novato encontrar seu próprio espaço."),
    ("rookie_arrival", "order_gear"): ("Ritual de vestiário", "A provocação vira assunto no grupo e nem todos entendem a brincadeira do mesmo jeito."),
    ("armband_dispute", "ask"): ("Conversa produtiva", "Você apresenta seus argumentos ao treinador, que reconhece sua importância dentro do grupo."),
    ("armband_dispute", "claim_leader"): ("Declaração forte", "Você afirma publicamente que se considera o verdadeiro líder do elenco. A frase rapidamente vira assunto."),
    ("squad_clique", "neutral"): ("Fora da disputa", "Você prefere não escolher lados e mantém distância da divisão interna."),
    ("squad_clique", "confront"): ("Confronto aberto", "Sua tentativa de enfrentar a panelinha transforma uma tensão silenciosa em conflito aberto."),
    ("provocative_question", "blame_team"): ("Crítica aos companheiros", "Você divide a responsabilidade com o restante do elenco, e a declaração não passa despercebida no vestiário."),
    ("provocative_question", "blame_coach"): ("Crítica ao comando", "Você aponta diretamente para as decisões do treinador. A resposta rapidamente vira destaque da coletiva."),
    ("reporter_argument", "answer_calmly"): ("Entrevista encerrada", "Você decide não alimentar a discussão e impede que a coletiva fique ainda mais tensa."),
    ("reporter_argument", "attack_reporter"): ("Resposta afiada", "Você rebate a pergunta sem esconder a irritação. A troca de palavras chama atenção da imprensa."),
    ("became_meme", "complain"): ("Você não achou graça", "Sua irritação pública acaba dando ainda mais combustível para a brincadeira."),
    ("became_meme", "ignore"): ("Sem dar palco", "Você prefere não comentar e espera que o assunto desapareça sozinho."),
    ("commercial_invitation", "accept"): ("Novo trabalho fora de campo", "Você aceita participar da campanha e passa a aparecer também fora do ambiente esportivo."),
    ("commercial_invitation", "focus"): ("Foco no futebol", "Você agradece o convite, mas prefere manter a atenção completamente voltada para sua carreira."),
    ("ishowspeed_video", "participate"): ("Encontro inusitado", "Você participa da gravação e o encontro rapidamente chama atenção nas redes sociais."),
    ("ishowspeed_video", "decline"): ("Convite recusado", "Você prefere não participar e segue normalmente com seus compromissos."),
    ("stalker_training", "ignore"): ("Você decide ignorar", "Você tenta tratar a situação como algo passageiro e segue sua rotina."),
    ("stalker_training", "tell_club"): ("Clube avisado", "Você comunica a situação internamente e o clube passa a prestar mais atenção ao que acontece ao seu redor."),
    ("stalker_training", "seek_authorities"): ("Você procura ajuda", "Você decide tratar a situação com seriedade e procura apoio para proteger sua segurança."),
    ("gambling_all_salary", "seek_help"): ("Hora de pedir ajuda", "Você reconhece que perdeu o controle da situação e procura apoio para tentar reorganizar sua vida."),
    ("gambling_all_salary", "hide_problem"): ("Problema escondido", "Você decide não contar a ninguém e tenta lidar sozinho com as consequências."),
}
for (_event_key, _choice_id), (_title, _text) in _CHOICE_RESULT_COPY.items():
    _choice = next((item for item in NARRATIVE_EVENTS[_event_key]["choices"] if item["id"] == _choice_id), None)
    if _choice:
        _choice.update(result_title=_title, result_text=_text)


def _set_choice_outcomes(event_key, choice_id, outcomes):
    """Mantém a variação probabilística como dado declarativo do catálogo."""
    choice = next(item for item in NARRATIVE_EVENTS[event_key]["choices"] if item["id"] == choice_id)
    choice.pop("effects", None)
    choice["outcomes"] = outcomes


_set_choice_outcomes("locker_room_authority", "listen_first", [
    {"weight": 80, "text": "Você ouviu o grupo e conduziu a conversa.", "effects": {"reputation": {"leadership": 3, "locker_room": 4}}},
    {"weight": 20, "text": "A postura surpreendeu positivamente o elenco.", "effects": {"reputation": {"leadership": 5, "locker_room": 6}, "player": {"morale": 2}}},
])
_set_choice_outcomes("locker_room_authority", "impose_authority", [
    {"weight": 60, "text": "Você impôs sua autoridade ao elenco.", "effects": {"reputation": {"leadership": 5, "locker_room": -6, "controversy": 4}, "behavior": {"authoritarian_choices": 1}}},
    {"weight": 30, "text": "O grupo aceitou sua liderança, ainda que com ressalvas.", "effects": {"reputation": {"leadership": 7, "locker_room": -2}, "behavior": {"authoritarian_choices": 1}}},
    {"weight": 10, "text": "Alguns jogadores se revoltaram com a postura.", "effects": {"reputation": {"locker_room": -10, "controversy": 7}, "status_momentum": -2}},
])
_set_choice_outcomes("rookie_arrival", "welcome", [
    {"weight": 75, "text": "Você ajudou o novato a se adaptar.", "effects": {"reputation": {"locker_room": 4, "leadership": 3}}},
    {"weight": 25, "text": "O novato se aproximou e ganhou confiança ao seu lado.", "effects": {"reputation": {"locker_room": 6, "leadership": 4}, "player": {"morale": 2}}},
])
_set_choice_outcomes("armband_dispute", "accept", [
    {"weight": 80, "text": "Você aceitou a decisão com profissionalismo.", "effects": {"reputation": {"discipline": 3, "locker_room": 1}}},
    {"weight": 20, "text": "O treinador valorizou sua postura.", "effects": {"reputation": {"discipline": 4, "leadership": 2}, "status_momentum": 1}},
])
_set_choice_outcomes("provocative_question", "take_responsibility", [
    {"weight": 75, "text": "Você assumiu a responsabilidade pela derrota.", "effects": {"reputation": {"media": 3, "leadership": 2}}},
    {"weight": 25, "text": "A postura foi muito elogiada na coletiva.", "effects": {"reputation": {"media": 5, "leadership": 4}, "player": {"morale": 2}}},
])
_set_choice_outcomes("became_meme", "join_joke", [
    {"weight": 70, "text": "Você entrou na brincadeira com leveza.", "effects": {"reputation": {"fans": 3, "media": 3}, "player": {"morale": 2}}},
    {"weight": 20, "text": "O meme explodiu positivamente nas redes.", "effects": {"reputation": {"fans": 7, "media": 5}, "player": {"morale": 5}}},
    {"weight": 10, "text": "A brincadeira piorou um pouco a situação.", "effects": {"reputation": {"controversy": 2, "media": -1}}},
])
_set_choice_outcomes("fan_song", "thank", [
    {"weight": 70, "text": "Você agradeceu à torcida pela homenagem.", "effects": {"reputation": {"fans": 5}, "player": {"morale": 4}}},
    {"weight": 25, "text": "A música virou símbolo da sua temporada.", "effects": {"reputation": {"fans": 8}, "player": {"morale": 6}, "development_points": 2}},
    {"weight": 5, "text": "A homenagem continuou como um carinho discreto da torcida.", "effects": {"reputation": {"fans": 3}}},
])
_set_choice_outcomes("health_diagnosis", "treat", [
    {"weight": 65, "text": "O tratamento exige paciência e uma pausa na rotina.", "effects": {"player": {"morale": -5, "form": -4}}},
    {"weight": 25, "text": "A recuperação respondeu bem aos cuidados.", "effects": {"player": {"morale": -2, "form": -2, "fatigue": -5}}},
    {"weight": 10, "text": "A recuperação demorará mais do que o esperado.", "effects": {"player": {"morale": -8, "form": -8}, "status_momentum": -2}},
])
_set_choice_outcomes("overdose_emergency", "treatment", [
    {"weight": 65, "text": "O tratamento foi iniciado e sua recuperação exigirá cuidado.", "effects": {"player": {"morale": -10, "form": -7}, "reputation": {"media": -5, "discipline": -6}}},
    {"weight": 25, "text": "O quadro se mostrou mais grave do que parecia.", "effects": {"player": {"morale": -15, "form": -12, "fatigue": 15}, "reputation": {"media": -7}, "status_momentum": -3}},
    {"weight": 8, "text": "A emergência deixou uma consequência física persistente.", "effects": {"player": {"overall": -1, "form": -12, "morale": -15}}},
    {"weight": 2, "text": "A emergência encerrou tragicamente sua história.", "effects": {"terminal": {"type": "death", "reason": "Uma emergência médica fora de campo encerrou sua trajetória."}}},
])
_set_choice_outcomes("leave_football", "keep_fighting", [
    {"weight": 65, "text": "Você decidiu seguir lutando pela carreira.", "effects": {"reputation": {"leadership": 2}, "player": {"morale": 3}}},
    {"weight": 25, "text": "A decisão renovou sua motivação.", "effects": {"player": {"morale": 8}, "development_points": 4, "status_momentum": 1}},
    {"weight": 10, "text": "As dificuldades continuam, apesar da decisão.", "effects": {"player": {"morale": -2}}},
])

_ensure_contextual_result_fields()


def _add_history(career, kind, text):
    career["history"].insert(0, {"kind": kind, "text": text})
    del career["history"][24:]


def normalize_narrative_state(career):
    """Inicializa campos novos para carreiras existentes sem sobrescrever dados."""
    reputation = career.setdefault("reputation", {})
    for key in REPUTATION_KEYS:
        reputation.setdefault(key, 0)
    behavior = career.setdefault("behavior", {})
    for key in BEHAVIOR_KEYS:
        behavior.setdefault(key, 0)
    career.setdefault("flags", {})
    career.setdefault("nicknames", [])
    career.setdefault("event_cooldowns", {})
    career.setdefault("event_seen", [])
    career.setdefault("scheduled_follow_ups", [])
    career.setdefault("narrative_event_season", None)
    return career


def _today(career):
    return date.fromisoformat(career["calendar"]["date"])


def _value_in_condition(value, expected):
    values = expected if isinstance(expected, (list, tuple, set)) else [expected]
    return value in values


def _current_club_size(career):
    """Classifica o clube atual a partir dos dados permanentes do SQLite."""
    club_id = career.get("club_id")
    club = get_club(club_id) if club_id else None
    if not club:
        return None
    score = (club["reputation"] + club["strength"]) / 2
    return "small" if score < 56 else "medium" if score < 73 else "big"


def event_is_eligible(career, event):
    """Valida condições declarativas antes de um evento entrar no fluxo."""
    normalize_narrative_state(career)
    if career.get("status") != "active" or event.get("disabled"):
        return False
    key = event.get("key") or event.get("event_key") or event.get("id")
    if not key:
        return False
    if event.get("unique") and key in career["event_seen"]:
        return False
    cooldown_until = career["event_cooldowns"].get(key)
    if cooldown_until and _today(career) < date.fromisoformat(cooldown_until):
        return False
    conditions = event.get("conditions", {})
    player = career["player"]
    bounds = {
        "age": player["age"], "overall": player["overall"], "morale": player["morale"],
        "form": player["form"], "fatigue": player["fatigue"], "matches": player["matches"], "games": player["matches"],
        "goals": player["goals"], "titles": len(career["titles"]),
    }
    for name, value in bounds.items():
        minimum, maximum = conditions.get(f"min_{name}"), conditions.get(f"max_{name}")
        if minimum is not None and value < minimum:
            return False
        if maximum is not None and value > maximum:
            return False
    if "country" in conditions and not _value_in_condition(player["country"], conditions["country"]):
        return False
    if "excluded_countries" in conditions and _value_in_condition(player["country"], conditions["excluded_countries"]):
        return False
    if "club" in conditions and not _value_in_condition(career.get("club"), conditions["club"]):
        return False
    if "club_size" in conditions and not _value_in_condition(_current_club_size(career), conditions["club_size"]):
        return False
    if "mode" in conditions and not _value_in_condition(career["mode"], conditions["mode"]):
        return False
    if "status" in conditions and not _value_in_condition(career["status"], conditions["status"]):
        return False
    if conditions.get("without_club") and career.get("club"):
        return False
    if "international_travel" in conditions and career.get("international_travel", False) != conditions["international_travel"]:
        return False
    competition_state = competition_context(career)
    for key in ("in_relegation_zone", "in_title_race", "league_status"):
        if key in conditions and competition_state.get(key) != conditions[key]:
            return False
    for reputation_key, minimum in conditions.get("min_reputation", {}).items():
        if career["reputation"].get(reputation_key, 0) < minimum:
            return False
    for reputation_key, maximum in conditions.get("max_reputation", {}).items():
        if career["reputation"].get(reputation_key, 0) > maximum:
            return False
    for behavior_key, minimum in conditions.get("min_behavior", {}).items():
        if career["behavior"].get(behavior_key, 0) < minimum:
            return False
    for behavior_key, maximum in conditions.get("max_behavior", {}).items():
        if career["behavior"].get(behavior_key, 0) > maximum:
            return False
    for flag in conditions.get("required_flags", []):
        if not career["flags"].get(flag):
            return False
    for flag in conditions.get("absent_flags", []):
        if career["flags"].get(flag):
            return False
    for nickname in conditions.get("has_nicknames", []):
        if nickname not in career["nicknames"]:
            return False
    for nickname in conditions.get("without_nicknames", []):
        if nickname in career["nicknames"]:
            return False
    return True


def build_narrative_event(career, event_key):
    definition = NARRATIVE_EVENTS.get(event_key)
    if not definition or not event_is_eligible(career, definition):
        return None
    event = deepcopy(definition)
    event["id"] = None
    event["event_key"] = definition["key"]
    event["narrative_event"] = True
    return event


def eligible_narrative_events(career, accelerated=False, normal_only=False):
    events = []
    for key, definition in NARRATIVE_EVENTS.items():
        event = build_narrative_event(career, key)
        has_terminal = any(
            "terminal" in item.get("effects", {})
            or any("terminal" in outcome.get("effects", {}) for outcome in item.get("outcomes", []))
            for item in (event or {}).get("choices", [])
        )
        if event and (not normal_only or (event["rarity"] in {"common", "uncommon", "rare"} and not has_terminal)):
            events.append(event)
    return events


def update_event_cooldown(career, event):
    key = event.get("event_key") or event.get("key") or event.get("id")
    if not key:
        return
    cooldown_weeks = event.get("cooldown", 0)
    if cooldown_weeks:
        career["event_cooldowns"][key] = (_today(career) + timedelta(weeks=cooldown_weeks)).isoformat()
    if event.get("unique") and key not in career["event_seen"]:
        career["event_seen"].append(key)


def schedule_follow_up(career, follow_up):
    event_key = follow_up.get("event_key")
    if event_key not in NARRATIVE_EVENTS:
        return
    weeks = max(0, int(follow_up.get("after_weeks", 0)))
    weeks += max(0, int(follow_up.get("after_months", 0))) * 4
    due_date = _today(career) + timedelta(weeks=weeks)
    target_season = career["calendar"]["season"] + 1 if follow_up.get("next_season") else None
    scheduled = career["scheduled_follow_ups"]
    if any(item["event_key"] == event_key for item in scheduled):
        return
    scheduled.append({"event_key": event_key, "due_date": due_date.isoformat(), "target_season": target_season})


def due_follow_up_events(career):
    """Retorna eventos futuros que chegaram à data e remove apenas os liberados."""
    if career.get("status") != "active":
        career["scheduled_follow_ups"] = []
        return []
    today = _today(career)
    ready, remaining = [], []
    for scheduled in career["scheduled_follow_ups"]:
        season_ready = not scheduled.get("target_season") or career["calendar"]["season"] >= scheduled["target_season"]
        if date.fromisoformat(scheduled["due_date"]) <= today and season_ready:
            event = build_narrative_event(career, scheduled["event_key"])
            if event:
                ready.append(event)
                continue
        remaining.append(scheduled)
    career["scheduled_follow_ups"] = remaining
    return ready


def evaluate_nicknames(career):
    """Concede apelidos uma vez, com base no estado persistente da carreira."""
    normalize_narrative_state(career)
    reputation, behavior = career["reputation"], career["behavior"]
    if (
        "Ditador" not in career["nicknames"]
        and behavior["authoritarian_choices"] >= 3
        and reputation["leadership"] >= 12
        and reputation["locker_room"] <= -12
    ):
        career["nicknames"].append("Ditador")
        _add_history(career, "apelido", 'Você recebeu o apelido "Ditador" pela postura no vestiário.')


def apply_event_effects(career, effects):
    """Aplica efeitos declarativos sem executar código fornecido por eventos."""
    normalize_narrative_state(career)
    effects = effects or {}
    player = career["player"]
    player_effects = {**effects.get("player", {}), **{key: effects[key] for key in PLAYER_EFFECT_KEYS if key in effects}}
    for key in PLAYER_EFFECT_KEYS:
        if key in player_effects:
            lower, upper = (38, 99) if key == "overall" else (0, 100)
            player[key] = max(lower, min(upper, player[key] + player_effects[key]))
    if "development_points" in effects:
        career["development_points"] = max(0, career.get("development_points", 0) + effects["development_points"])
    if "status_momentum" in effects:
        career["status_momentum"] = max(-12, min(12, career.get("status_momentum", 0) + effects["status_momentum"]))
    for key, delta in effects.get("reputation", {}).items():
        if key in REPUTATION_KEYS:
            career["reputation"][key] = max(-100, min(100, career["reputation"][key] + delta))
    for key, delta in effects.get("behavior", {}).items():
        if key in BEHAVIOR_KEYS:
            career["behavior"][key] = max(0, career["behavior"][key] + delta)
    flags_to_set = effects.get("set_flags", [])
    if isinstance(flags_to_set, dict):
        career["flags"].update(flags_to_set)
    else:
        for flag in flags_to_set:
            career["flags"][flag] = True
    for flag in effects.get("clear_flags", []):
        career["flags"][flag] = False
    for nickname in effects.get("nicknames", []):
        if nickname not in career["nicknames"]:
            career["nicknames"].append(nickname)
            _add_history(career, "apelido", f'Você recebeu o apelido "{nickname}".')
    history = effects.get("history")
    if history:
        entries = history if isinstance(history, list) else [history]
        for text in entries:
            _add_history(career, "decisão", text)
    for follow_up in effects.get("follow_ups", []):
        schedule_follow_up(career, follow_up)
    evaluate_nicknames(career)
    terminal = effects.get("terminal")
    if terminal:
        apply_terminal_effect(career, terminal, effects.get("event_id"))


def _weighted_outcome(career, outcomes, rng=None):
    """Escolhe exatamente um resultado com a RNG persistente da carreira."""
    weighted = [(outcome, max(0, outcome.get("weight", 1))) for outcome in outcomes]
    total = sum(weight for _, weight in weighted)
    if total <= 0:
        return weighted[0][0] if weighted else None
    if rng is None:
        career["random_step"] = career.get("random_step", 0) + 1
        rng = random.Random(career["random_seed"] + career["random_step"] * 7919)
    target = rng.random() * total
    for outcome, weight in weighted:
        target -= weight
        if target < 0:
            return outcome
    return weighted[-1][0]


def _outcome_result_event(career, source_key, title, outcome):
    return {
        "id": None, "type": "outcome", "title": outcome.get("result_title", title),
        "text": contextual_text(outcome.get("result_text") or outcome.get("text") or "A consequência da sua decisão foi registrada.", career),
        "choices": [{"id": "continue", "label": "Continuar"}], "outcome_result": True,
        "source_event_key": source_key, "outcome_summary": outcome.get("summary", []),
    }


def apply_action_outcome(career, action, source_key, rng=None):
    """Aplica um outcome de ação voluntária e prepara seu card de confirmação."""
    outcomes = action.get("outcomes")
    if not outcomes:
        return None
    outcome = _weighted_outcome(career, outcomes, rng)
    apply_event_effects(career, outcome.get("effects", {}))
    return _outcome_result_event(career, source_key, action.get("result_title", action["label"]), outcome)


def resolve_narrative_event(career, event, choice_id, rng=None):
    choice = next((item for item in event.get("choices", []) if item["id"] == choice_id), None)
    if not choice:
        return False
    outcome = _weighted_outcome(career, choice["outcomes"], rng) if choice.get("outcomes") else None
    effects = dict((outcome or choice).get("effects") or {})
    if "terminal" in effects:
        effects["event_id"] = event.get("event_key") or event.get("key") or event.get("id")
    apply_event_effects(career, effects)
    update_event_cooldown(career, event)
    if outcome:
        return _outcome_result_event(career, event.get("event_key") or event.get("key") or event.get("id"), event["title"], outcome)
    return {"id": None, "type": "outcome", "title": choice.get("result_title", event["title"]),
            "text": contextual_text(choice.get("result_text") or event.get("text") or "A situação segue seu curso após sua decisão.", career),
            "choices": [{"id": "continue", "label": "Continuar"}], "outcome_result": True,
            "source_event_key": event.get("event_key"), "outcome_summary": choice.get("summary", [])}


def maybe_create_narrative_event(career, rng, chance=.045, accelerated=False, normal_only=False):
    """Escolhe um evento elegível de modo ponderado pelo fluxo existente."""
    if rng.random() >= chance:
        return None
    candidates = eligible_narrative_events(career, accelerated=accelerated, normal_only=normal_only)
    if not candidates:
        return None
    total = sum(RARITY_WEIGHTS[event["rarity"]] for event in candidates)
    target = rng.random() * total
    for event in candidates:
        target -= RARITY_WEIGHTS[event["rarity"]]
        if target < 0:
            return event
    return candidates[-1]

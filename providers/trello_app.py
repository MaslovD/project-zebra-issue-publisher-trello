import base64

from trello import TrelloClient


def name(body, *args, **kwargs):
    return body.get('name', 'Custom issue')


def desc(body, *args, **kwargs):
    return body.get('arbitraryDescription', '') + contact(body)


def labels(body, board, *args, **kwargs):
    list_labels = [(i.get('name', 'no name'), i.get('color', 'none'), board) for i in body.get('labels', {})]
    return [create_label_safe(*i) for i in list_labels]


def contact(body, *args, **kwargs):
    contact_info_plain = body.get('contactInfo', '')
    if contact_info_plain != '':
        return CONTACT_FORMAT.format(contact_info_plain)
    return ""


def assign(body, board, *args, **kwargs):
    users = body.get('assigneeList', [])
    return list(filter(lambda member: member.username in users, board.all_members()))


TRELLO_LIST_PUSH_NAME = "backlog"


def trello_list(board):
    list_lists = board.open_lists()
    if TRELLO_LIST_PUSH_NAME in list(map(str.lower, [l.name for l in list_lists])):
        return list_lists[list(map(str.lower, [l.name for l in list_lists])).index(TRELLO_LIST_PUSH_NAME)]
    return board.add_list(TRELLO_LIST_PUSH_NAME, 0)


def trello_board(api_key, token, url):
    return list(filter(lambda b: b.url.startswith(url), TrelloClient(api_key=api_key, token=token).list_boards()))[0]


def create_label_safe(lname, color, board):
    list_labels = {(i.name, i.color): i for i in board.get_labels()}
    if (lname, color) in list_labels.keys():
        return list_labels[(lname, color)]
    else:
        return board.add_label(lname, color)


def attach_file(attach_body, card):
    name = attach_body.get("name", "attachment")
    mimeType = attach_body.get("mimeType", "image/png")
    file = attach_body.get("file", "")
    url = attach_body.get("url", "")
    if file != "":
        card.attach(name=name, mimeType=mimeType, file=base64.b64decode(file))
    elif url != "":
        card.attach(name=name, mimeType=mimeType, url=url)
    else:
        raise NotImplementedError


def push_card(trello_api_key, trello_token, body):
    board = trello_board(
        trello_api_key,
        trello_token,
        body.get('board_url', "https://trello.com/b/uEd50g7X"))
    card = trello_list(board).add_card(
        **{i[0]: i[1](body, board) for i in TRELLO_MAPPING.items()})
    for attachment in body.get("attachments", []):
        attach_file(attachment, card)


TRELLO_MAPPING = {'name': name,
                  'desc': desc,
                  'labels': labels,
                  'assign': assign
                  }

CONTACT_FORMAT = """

Contact info:
----------------------
*{}*
"""

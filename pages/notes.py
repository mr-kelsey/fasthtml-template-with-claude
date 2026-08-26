from fasthtml import common as fast
from layout import layout
import db

router = fast.APIRouter()


def _note_row(note):
    return fast.Tr(
        fast.Td(note["title"]),
        fast.Td(note["body"]),
        fast.Td(str(note["created_at"])),
        fast.Td(
            fast.Form(
                fast.Button("Delete", type="submit"),
                method="post",
                action=f"/notes/{note['id']}/delete",
            )
        ),
    )


@router("/notes", methods=["get"])
def list_notes_page():
    notes = db.list_notes()
    rows = [_note_row(n) for n in notes] if notes else [fast.Tr(fast.Td("No notes yet.", colspan="4"))]
    table = fast.Table(
        fast.Thead(fast.Tr(fast.Th("Title"), fast.Th("Note"), fast.Th("Created"), fast.Th(""))),
        fast.Tbody(*rows),
    )
    add_form = fast.Form(
        fast.Input(name="title", placeholder="Title", required=True),
        fast.Textarea(name="body", placeholder="Write a note...", required=True),
        fast.Button("Add Note", type="submit"),
        method="post",
        action="/notes",
    )
    return layout(
        "Notes",
        fast.H1("Notes"),
        fast.H2("Add a note"),
        add_form,
        fast.H2("All notes"),
        table,
    )


@router("/notes", methods=["post"])
def add_note_route(title: str, body: str):
    title = title.strip()
    body = body.strip()
    if not title or not body:
        return fast.Response("Title and body are required.", status_code=422)
    db.add_note(title, body)
    return fast.Redirect("/notes")


@router("/notes/{note_id}/delete", methods=["post"])
def delete_note_route(note_id: int):
    db.delete_note(note_id)
    return fast.Redirect("/notes")

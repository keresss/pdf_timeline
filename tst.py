import streamlit as st
import pandas as pd
import plotly.express as px
import json
import base64
from streamlit_pdf_viewer import pdf_viewer

def show_pdf(path: str, page: int, width="100%"):
    # you can pass the file path directly, it will read and render it
    pdf_viewer(
        input=path,
        width=width,
        # pages_to_render takes a list of page numbers (1-based):
        pages_to_render=[page]
    )

if "pdf_page" not in st.session_state:
    st.session_state.pdf_page = None

# Cache data loading for performance
@st.cache_data
def load_data(json_path="up_in_flames_graph.json"):
    with open(json_path, 'r', encoding='utf-8') as f:
        data = json.load(f)

    # Flatten JSON into rows
    rows = []
    for item in data:
        chunk_id = item.get("chunk_id")
        page = item.get("page")
        part = item.get("part_title")
        chapter = item.get("chapter_title")
        section = item.get("section_title")
        mo = item.get("model_output", {})

        # Events
        for e in mo.get("events", []):
            date = e.get("date")
            if date:
                rows.append({
                    "date": date,
                    "type": "Event",
                    "label": e.get("label"),
                    "description": e.get("description"),
                    "actors": ", ".join(e.get("actors", [])),
                    "location": None,
                    "witness": None,
                    "chunk_id": chunk_id,
                    "page": page,
                    "part": part,
                    "chapter": chapter,
                    "section": section
                })

        # Testimonies
        for t in mo.get("testimonies", []):
            date = t.get("date")
            if date:
                rows.append({
                    "date": date,
                    "type": "Testimony",
                    "label": f"Testimony - {t.get('witness')}",
                    "description": t.get("excerpt"),
                    "actors": None,
                    "location": t.get("location"),
                    "witness": t.get("witness"),
                    "chunk_id": chunk_id,
                    "page": page,
                    "part": part,
                    "chapter": chapter,
                    "section": section
                })

        # Violations
        for v in mo.get("violations", []):
            date = v.get("date")
            if date:
                party = v.get("actors") if v.get("actors") else v.get("party")
                actors_str = ", ".join(party) if isinstance(party, list) else party
                rows.append({
                    "date": date,
                    "type": "Violation",
                    "label": v.get("label") or v.get("description"),
                    "description": v.get("description"),
                    "actors": actors_str,
                    "location": None,
                    "witness": None,
                    "chunk_id": chunk_id,
                    "page": page,
                    "part": part,
                    "chapter": chapter,
                    "section": section
                })

    df = pd.DataFrame(rows)
    # Convert dates
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df = df.dropna(subset=['date'])
    return df


def main():
    st.set_page_config(page_title="Conflict Timeline Explorer", layout="wide")
    st.title("Conflict Timeline Explorer")

    # Load data
    df = load_data()

    # Two-column layout: left for controls+data, right for PDF
    left_col, right_col = st.columns([2.5, 2.5])

    # Filters & timeline in left column
    with left_col:
        st.header("Filters")
        min_date = df['date'].min().date()
        max_date = df['date'].max().date()
        date_range = st.date_input("Date Range", [min_date, max_date])

        types = df['type'].unique().tolist()
        selected_types = st.multiselect("Event Types", types, default=types)

        actors_expanded = []
        for a in df['actors'].dropna():
            actors_expanded.extend([x.strip() for x in a.split(',')])
        actors_list = sorted(set(actors_expanded))
        selected_actors = st.multiselect("Actors", actors_list)

        # Apply filters
        mask = (
            (df['date'] >= pd.to_datetime(date_range[0])) &
            (df['date'] <= pd.to_datetime(date_range[1])) &
            df['type'].isin(selected_types)
        )
        if selected_actors:
            mask &= df['actors'].str.contains('|'.join(selected_actors), na=False)
        filtered = df[mask]

        # Timeline as scatter
        st.header("Timeline")
        if not filtered.empty:
            fig = px.scatter(
                filtered,
                x='date',
                y='type',
                color='type',
                hover_name='label',
                hover_data=['description', 'actors', 'location', 'chunk_id', 'page'],
                height=300
            )
            fig.update_yaxes(categoryorder="array", categoryarray=["Event","Violation","Testimony"])
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("No records found for selected filters.")

        # Records list
        st.header("Records")
        for idx, (_, row) in enumerate(filtered.sort_values('date').iterrows()):
            with st.expander(f"{row['date'].date()} – {row['label']}"):
                if row['actors']:
                    st.write(f"**Actors:** {row['actors']}")
                if row['witness']:
                    st.write(f"**Witness:** {row['witness']}")
                if row['location']:
                    st.write(f"**Location:** {row['location']}")
                st.write(f"**Description:** {row['description']}")
                st.write(f"**Source:** chunk `{row['chunk_id']}`, page {row['page']}")
                st.write(f"**Part:** {row['part']} > **Chapter:** {row['chapter']} > **Section:** {row['section']}")

                # Set PDF page on click
                btn_key = f"pdf_btn_{idx}_{row['chunk_id']}"
                if st.button(f"View page {row['page']} in PDF", key=btn_key):
                    st.session_state.pdf_page = row['page']

    # PDF viewer in right column
    with right_col:
        st.header("Document Viewer")
        if st.session_state.pdf_page:
            st.markdown(f"### Showing PDF page {st.session_state.pdf_page}")
            show_pdf("georgia0109web.pdf", st.session_state.pdf_page)
        else:
            st.write("Click a record's button on the left to view the PDF page here.")

    # Footer note
    st.markdown(
        """
        **Note:** To view the full context, open the PDF at the specified page number and locate the chunk ID.
        """
    )

if __name__ == "__main__":
    main()

from typing import List, Dict
import pickle
import json
import datetime
from pathlib import Path

import yaml
import typer
import pandas as pd
import pytz

from acl_miniconf.data import Session, Event, Paper, Conference


DATE_FMT = '%Y-%m-%d %H:%M'


def clean_authors(authors: List[str]):
    return [a.strip() for a in authors]

def parse_authors(author_string: str):
    authors = author_string.split(',')
    if len(authors) == 1:
        authors = authors[0].split(' and ')
        return clean_authors(authors)
    else:
        front_authors = authors[:-1]
        last_authors = authors[-1].split(' and ')
        return clean_authors(front_authors + last_authors)


def parse_sessions_and_tracks(df: pd.DataFrame):
    sessions = sorted(set(df.Session.values), key=lambda x: int(x.split()[1]))
    tracks = sorted(set(df.Track.values))
    return sessions, tracks


def get_session_event_name(session: str, track: str, session_type: str):
    return f'{session}: {track} ({session_type})'


class Acl2023Parser:
    def __init__(self, *, oral_tsv_path: Path, poster_tsv_path: Path, virtual_tsv_path: Path):
        self.poster_tsv_path = poster_tsv_path
        self.oral_tsv_path = oral_tsv_path
        self.virtual_tsv_path = virtual_tsv_path
        self.papers: Dict[str, Paper] = {}
        self.sessions: Dict[str, Session] = {}
        self.events: Dict[str, Event] = {}
        self.zone = pytz.timezone('America/Toronto')
    
    def parse(self):
        self._parse_oral_papers(self.oral_tsv_path)
        self._parse_poster_papers(self.poster_tsv_path)
        self._parse_virtual_papers(self.virtual_tsv_path)
        return Conference(
            sessions=self.sessions,
            papers=self.papers,
            events=self.events
        )
    
    def _parse_start_end_dt(self, date_str: str, time_str: str):
        start_time, end_time = time_str.split('-')
        start_parsed_dt = self.zone.localize(datetime.datetime.strptime(f'{date_str} {start_time}', DATE_FMT))
        end_parsed_dt = self.zone.localize(datetime.datetime.strptime(f'{date_str} {end_time}', DATE_FMT))
        return start_parsed_dt, end_parsed_dt
    
    def _parse_virtual_papers(self, virtual_tsv_path: Path):
        df = pd.read_csv(virtual_tsv_path, sep='\t')
        group_type = 'Virtual Poster'
        for (group_session, group_track), group in df.groupby(['Session', 'Track']):
            group = group.sort_values('Local order')
            event_name = get_session_event_name(group_session, group_track, group_type)
            start_dt, end_dt = self._parse_start_end_dt(group.iloc[0].Date, group.iloc[0].Time)
            if event_name not in self.events:
                self.events[event_name] = Event(
                    id=event_name,
                    session=group_session,
                    track=group_track,
                    start_time=start_dt,
                    end_time=end_dt,
                    chairs=[],
                    paper_ids=[],
                    link=None,
                    room='Virtual Poster Session',
                    type=group_type,
                )
            event = self.events[event_name]
            if group_session not in self.sessions:
                self.sessions[group_session] = Session(
                    id=group_session,
                    name=group_session,
                    start_time=start_dt,
                    end_time=end_dt,
                    events=[],
                )
            session = self.sessions[group_session]
            if event_name in session.events:
                raise ValueError('Duplicated events')
            session.events[event_name] = event

            for row in group.itertuples():
                paper_id = row.PID
                start_dt, end_dt = self._parse_start_end_dt(row.Date, row.Time)
                event = self.events[event_name]
                event.paper_ids.append(paper_id)

    
    def _parse_poster_papers(self, poster_tsv_path: Path):
        df = pd.read_csv(poster_tsv_path, sep='\t')
        group_type = 'Poster'
        for (group_session, group_track), group in df.groupby(['Session', 'Track']):
            group = group.sort_values('Local order')
            event_name = get_session_event_name(group_session, group_track, group_type)
            start_dt, end_dt = self._parse_start_end_dt(group.iloc[0].Date, group.iloc[0].Time)
            if event_name not in self.events:
                self.events[event_name] = Event(
                    id=event_name,
                    session=group_session,
                    track=group_track,
                    start_time=start_dt,
                    end_time=end_dt,
                    chairs=[],
                    paper_ids=[],
                    link=None,
                    room='Poster Session',
                    type=group_type,
                )
            event = self.events[event_name]

            if group_session not in self.sessions:
                self.sessions[group_session] = Session(
                    id=group_session,
                    name=group_session,
                    start_time=start_dt,
                    end_time=end_dt,
                    events=[],
                )
            session = self.sessions[group_session]
            if event_name in session.events:
                raise ValueError('Duplicated events')
            session.events[event_name] = event

            for row in group.itertuples():
                paper_id = row.PID
                start_dt, end_dt = self._parse_start_end_dt(row.Date, row.Time)
                event = self.events[event_name]
                event.paper_ids.append(paper_id)


    def _parse_oral_papers(self, oral_tsv_path: Path):
        df = pd.read_csv(oral_tsv_path, sep='\t')
        group_type = 'Oral'
        for (group_session, group_track), group in df.groupby(['Session', 'Track']):
            group = group.sort_values('Track Order')
            room = group.iloc[0].Room
            event_name = get_session_event_name(group_session, group_track, group_type)
            start_dt, end_dt = self._parse_start_end_dt(group.iloc[0].Date, group.iloc[0].Time)
            if event_name not in self.events:
                self.events[event_name] = Event(
                    id=event_name,
                    session=group_session,
                    track=group_track,
                    start_time=start_dt,
                    end_time=end_dt,
                    chairs=[],
                    paper_ids=[],
                    link=None,
                    room=room,
                    type=group_type,
                )
            event = self.events[event_name]
            if group_session not in self.sessions:
                self.sessions[group_session] = Session(
                    id=group_session,
                    name=group_session,
                    start_time=start_dt,
                    end_time=end_dt,
                    events=[],
                )
            session = self.sessions[group_session]
            session.events[event_name] = event
            for row in group.itertuples():
                paper_id = row.PID
                event.paper_ids.append(paper_id)
                paper = Paper(
                    id=paper_id,
                    program='Main',
                    title=row.Title,
                    authors=parse_authors(row.Author),
                    track=group_track,
                    paper_type=row.Length,
                    abstract="",
                    tldr="",
                    keywords=[],
                    pdf_url="",
                    demo_url="",
                    event_ids=[event.id],
                    similar_paper_ids=[],
                    forum="",
                    card_image_path="",
                    presentation_id="",
                )
                if row.PID in self.papers:
                    raise ValueError('Duplicate papers')
                self.papers[row.PID] = paper

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, (datetime.datetime,)):
            return obj.isoformat()

def main(
    oral_tsv: str = 'sitedata/acl2023/oral-papers.tsv',
    poster_tsv: str = 'sitedata/acl2023/poster-papers.tsv',
    virtual_tsv: str = 'sitedata/acl2023/virtual-papers.tsv',
    out_dir: str = 'auto_data/acl_2023/',
):
    parser = Acl2023Parser(
        oral_tsv_path=Path(oral_tsv),
        poster_tsv_path=Path(poster_tsv),
        virtual_tsv_path=Path(virtual_tsv),
    )
    conf = parser.parse()
    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True, parents=True)
    conf_dict = conf.dict()
    with open(out_dir / 'program.yaml', 'w') as f:
        f.write(yaml.dump(conf_dict))

    with open(out_dir / 'program.json', 'w') as f:
        json.dump(conf_dict, f, cls=DateTimeEncoder)

    with open(out_dir / 'program.pkl', 'wb') as f:
        pickle.dump(conf, f)


if __name__ == '__main__':
    typer.run(main)

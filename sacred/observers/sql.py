#!/usr/bin/env python
# coding=utf-8
from __future__ import division, print_function, unicode_literals
import os.path

import sqlalchemy as sa
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from sacred.commandline_options import CommandLineOption
from sacred.dependencies import get_digest
from sacred.observers.base import RunObserver

# ################################ ORM ###################################### #
Base = declarative_base()


class Source(Base):
    __tablename__ = 'source'

    @classmethod
    def create(cls, filename):
        md5sum = get_digest(filename)
        with open(filename, 'r') as f:
            return cls(filename=filename, md5sum=md5sum, content=f.read())

    id = sa.Column(sa.Integer, primary_key=True)
    filename = sa.Column(sa.String(256))
    md5sum = sa.Column(sa.String(32))
    content = sa.Column(sa.Text)


class Dependency(Base):
    __tablename__ = 'dependency'

    @classmethod
    def create(cls, name, version):
        return cls(name=name, version=version)

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(32))
    version = sa.Column(sa.String(16))


class Artifact(Base):
    __tablename__ = 'artifact'

    @classmethod
    def create(cls, filename):
        head, tail = os.path.split(filename)
        with open(filename, 'rb') as f:
            return cls(filename=tail, content=f.read())

    id = sa.Column(sa.Integer, primary_key=True)
    filename = sa.Column(sa.String(64))
    content = sa.Column(sa.LargeBinary)

    run_id = sa.Column(sa.Integer, sa.ForeignKey('run.id'))
    run = sa.orm.relationship("Run", backref=sa.orm.backref('artifacts'))


class Resource(Base):
    __tablename__ = 'resource'

    @classmethod
    def create(cls, filename):
        md5sum = get_digest(filename)
        with open(filename, 'rb') as f:
            return cls(filename=filename, md5sum=md5sum, content=f.read())

    id = sa.Column(sa.Integer, primary_key=True)
    filename = sa.Column(sa.String(256))
    md5sum = sa.Column(sa.String(32))
    content = sa.Column(sa.LargeBinary)


class Host(Base):
    __tablename__ = 'host'

    id = sa.Column(sa.Integer, primary_key=True)
    cpu = sa.Column(sa.String(64))
    cpu_count = sa.Column(sa.Integer)
    hostname = sa.Column(sa.String(64))
    os = sa.Column(sa.String(16))
    os_info = sa.Column(sa.String(64))
    python_version = sa.Column(sa.String(16))
    python_compiler = sa.Column(sa.String(64))

experiment_source_association = sa.Table(
    'experiments_sources', Base.metadata,
    sa.Column('experiment_id', sa.Integer, sa.ForeignKey('experiment.id')),
    sa.Column('source_id', sa.Integer, sa.ForeignKey('source.id'))
)

experiment_dependency_association = sa.Table(
    'experiments_dependencies', Base.metadata,
    sa.Column('experiment_id', sa.Integer, sa.ForeignKey('experiment.id')),
    sa.Column('dependency_id', sa.Integer, sa.ForeignKey('dependency.id'))
)


class Experiment(Base):
    __tablename__ = 'experiment'

    id = sa.Column(sa.Integer, primary_key=True)
    name = sa.Column(sa.String(32))
    doc = sa.Column(sa.Text)

    sources = sa.orm.relationship("Source",
                                  secondary=experiment_source_association,
                                  backref="experiments")
    dependencies = sa.orm.relationship(
        "Dependency",
        secondary=experiment_dependency_association,
        backref="experiments")


run_resource_association = sa.Table(
    'runs_resources', Base.metadata,
    sa.Column('run_id', sa.Integer, sa.ForeignKey('run.id')),
    sa.Column('resource_id', sa.Integer, sa.ForeignKey('resource.id'))
)


class Run(Base):
    __tablename__ = 'run'

    id = sa.Column(sa.Integer, primary_key=True)

    start_time = sa.Column(sa.DateTime)
    heartbeat = sa.Column(sa.DateTime)
    stop_time = sa.Column(sa.DateTime)

    comment = sa.Column(sa.Text)
    captured_out = sa.Column(sa.Text)
    fail_trace = sa.Column(sa.Text)
    config = sa.Column(sa.Text)
    info = sa.Column(sa.Text)

    status = sa.Column(sa.Enum("RUNNING", "COMPLETED", "INTERRUPTED",
                               "FAILED"))

    host_id = sa.Column(sa.Integer, sa.ForeignKey('host.id'))
    host = sa.orm.relationship("Host", backref=sa.orm.backref('runs'))

    experiment_id = sa.Column(sa.Integer, sa.ForeignKey('experiment.id'))
    experiment = sa.orm.relationship("Experiment",
                                     backref=sa.orm.backref('runs'))

    # artifacts = backref
    resources = sa.orm.relationship("Resource",
                                    secondary=run_resource_association,
                                    backref="runs")


# ############################# Observer #################################### #

class SqlObserver(RunObserver):
    @classmethod
    def create(cls, url, echo=True):
        engine = sa.create_engine(url, echo=echo)
        Session = sessionmaker(bind=engine)
        return cls(engine, Session())

    def __init__(self, engine, session):
        self.engine = engine
        self.session = session

    def started_event(self, ex_info, host_info, start_time, config, comment):
        Base.metadata.create_all(self.engine)

    def heartbeat_event(self, info, captured_out, beat_time):
        pass

    def completed_event(self, stop_time, result):
        pass

    def interrupted_event(self, interrupt_time):
        pass

    def failed_event(self, fail_time, fail_trace):
        pass

    def resource_event(self, filename):
        pass

    def artifact_event(self, filename):
        pass


# ######################## Commandline Option ############################### #

class SqlOption(CommandLineOption):

    """Add a SQL Observer to the experiment."""

    arg = 'DB_URL'
    arg_description = "The typical form is: dialect://username:password@host:port/database"

    @classmethod
    def execute(cls, args, run):
        run.observers.append(SqlObserver.create(args))

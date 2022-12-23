#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:
from datetime import datetime

# 3rd party:
from sqlalchemy import text

# Internal:
try:
    from __app__.storage import StorageClient
    from __app__.db_tables.covid19 import Session
    from .utils import plot_thumbnail, plot_vaccinations, plot_vaccinations_50_plus
    from . import queries
except ImportError:
    from storage import StorageClient
    from db_tables.covid19 import Session
    from db_etl_homepage_graphs.utils import (
        plot_thumbnail, plot_vaccinations, plot_vaccinations_50_plus
    )
    from db_etl_homepage_graphs import queries
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

__all__ = [
    'main'
]


METRICS = [
    'newAdmissions',
    'newCasesByPublishDate',
    'newDeaths28DaysByPublishDate',
    'newCasesBySpecimenDate',
    'newDeaths28DaysByDeathDate',
    'newVirusTestsByPublishDate'
]


def store_data(date: str, metric: str, svg: str, area_type: str = None,
               area_code: str = None):
    kws = dict(
        container="downloads",
        content_type="image/svg+xml",
        cache_control="public, max-age=30, s-maxage=90, must-revalidate",
        compressed=False
    )

    path = f"homepage/{date}/thumbnail_{metric}.svg"

    if area_code is not None:
        path = f"homepage/{date}/{metric}/{area_type}/{area_code}_thumbnail.svg"

    with StorageClient(path=path, **kws) as cli:
        cli.upload(svg)


def upload_file(date: str, metric: str, svg: str, area_type: str = None,
                area_code: str = None):
    """
    This is used to save svg files into Azure Data Storage. The images are waffle charts
    used on the main page, and currently are related to people of age 50 and over.
    All the params, apart from 'svg', are used only to create the path to the file.

    :param date: date of the current release
    :param metric: metric that the image was generated for
    :param svg: data of the image
    :param area_type: type of the area for which the chart was created
    :param area_code: area code
    """
    kws = dict(
        container="downloads",
        content_type="image/svg+xml",
        cache_control="public, max-age=30, s-maxage=90, must-revalidate",
        compressed=False
    )

    if area_code is not None:
        path = f"homepage/{date}/{metric}/{area_type}/{area_code}_50_plus_thumbnail.svg"

        with StorageClient(path=path, **kws) as cli:
            cli.upload(svg)


def get_timeseries(date: str, metric: str):
    ts = datetime.strptime(date, "%Y-%m-%d")
    partition = f"{ts:%Y_%-m_%-d}_other"
    partition_id = f"{ts:%Y_%-m_%-d}|other"
    values_query = queries.TIMESRIES_QUERY.format(partition=partition)
    change_query = queries.LATEST_CHANGE_QUERY.format(partition=partition)

    session = Session()
    conn = session.connection()
    try:
        resp = conn.execute(
            text(values_query),
            partition_id=partition_id,
            metric=metric,
            datestamp=ts
        )
        values = resp.fetchall()

        resp = conn.execute(
            text(change_query),
            partition_id=partition_id,
            datestamp=ts,
            metric=metric + "Change"
        )
        change = resp.fetchone()
    except Exception as err:
        session.rollback()
        raise err
    finally:
        session.close()

    store_data(
        date,
        metric,
        plot_thumbnail(values, metric_name=metric, change=change)
    )

    return True


def get_value_50_plus(item: dict):
    """
    Get the values for the item in a list where its key 'age' is '50+'
    and put them in new dict. New keys:
    - cumPeopleVaccinatedAutumn22ByVaccinationDate
    - cumVaccinationAutumn22UptakeByVaccinationDatePercentage

    :param item: data from DB (1 row)
    :return: a dictionary with all the data to generate a svg file and the path to it
    :rtype: dict
    """
    vaccination_date = 0
    vaccination_date_percentage_dose = 0

    for obj in item['payload']:
        if obj.get('age') == '50+':
            vaccination_date = int(round(
                obj.get('cumPeopleVaccinatedAutumn22ByVaccinationDate', 0), 1
            ))
            vaccination_date_percentage_dose = int(round(
                obj.get('cumVaccinationAutumn22UptakeByVaccinationDatePercentage', 0), 1
            ))

    return {
        "area_type": item['area_type'],
        "area_code": item['area_code'],
        "date": item['date'],
        # These are the new keys/values that have to be provided to generate the image
        "vaccination_date": vaccination_date,
        "vaccination_date_percentage_dose": vaccination_date_percentage_dose
    }


def get_vaccinations(date):
    ts = datetime.strptime(date, "%Y-%m-%d")
    partition = f"{ts:%Y_%-m_%-d}"

    vax_query = queries.VACCINATIONS_QUERY.format(partition_date=partition)

    session = Session()
    conn = session.connection()
    try:
        resp = conn.execute(
            text(vax_query),
            datestamp=ts
        )
        values = resp.fetchall()
    except Exception as err:
        session.rollback()
        raise err
    finally:
        session.close()

    for item in values:
        store_data(
            date,
            "vaccinations",
            plot_vaccinations(item),
            area_type=item["area_type"],
            area_code=item["area_code"]
        )

    return True


def get_vaccinations_50_plus(date: str):
    """
    The function to get the data from database. It will also call other functions
    to generate SVG images (waffle charts)
    It returns True as the original function does

    :param date: date of the latest release
    :return: True
    :rtype: boolean
    """
    ts = datetime.strptime(date, "%Y-%m-%d")
    partition = f"{ts:%Y_%-m_%-d}"

    vax_query_50_plus = queries.VACCINATIONS_QUERY_50_PLUS.format(partition=partition)

    session = Session()
    conn = session.connection()
    try:
        resp50 = conn.execute(text(vax_query_50_plus))
        values_50_plus = resp50.fetchall()
    except Exception as err:
        session.rollback()
        raise err
    finally:
        session.close()

    # This is used to track the most recent value that will be used to generate the files
    saved_data = {}

    for item in values_50_plus:
        # Checking if it's the newest data for the region
        if (
            item['area_type'] not in saved_data
            or item['area_code'] not in saved_data[item['area_type']]
            or item['date'] > saved_data[item['area_type']][item['area_code']]
        ):
            # Updating the existing data or creating a new entry
            if item['area_type'] not in saved_data:
                saved_data[item['area_type']] = {item['area_code']: item['date']}
            elif item['area_code'] not in saved_data[item['area_type']]:
                saved_data[item['area_type']][item['area_code']] = item['date']

            upload_file(
                date,
                "vaccinations",
                plot_vaccinations_50_plus(get_value_50_plus(item)),
                area_type=item["area_type"],
                area_code=item["area_code"]
            )

    return True


def main(payload):
    category = payload.get("category", "main")

    if category == "main":
        for metric in METRICS:
            get_timeseries(payload['date'], metric)

    if payload.get("category") == "vaccination":
        get_vaccinations(payload['date'])
        get_vaccinations_50_plus(payload['date'])

    return f'DONE: {payload["date"]}'


if __name__ == "__main__":
    main({"date": "2022-08-10"})

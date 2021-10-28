#!/usr/bin python3

# Imports
# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
# Python:

# 3rd party:

# Internal: 

# ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~


VACCINATIONS_QUERY = """\
SELECT first.area_type,
       first.area_code,
       MAX(first.date)              AS date,
       MAX(FLOOR(first_dose))::INT  AS first_dose,
       MAX(FLOOR(second_dose))::INT AS second_dose,
       MAX(FLOOR(third_dose))::INT  AS third_dose
FROM (
         SELECT area_type,
                area_code,
                MAX(date)                        AS date,
                MAX((payload -> 'value')::FLOAT) AS first_dose
         FROM (
                  SELECT *
                  FROM covid19.time_series_p{partition_date}_other AS tm
                           JOIN covid19.release_reference AS rr ON rr.id = release_id
                           JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                           JOIN covid19.area_reference AS ar ON ar.id = tm.area_id
                  UNION
                  (
                      SELECT *
                      FROM covid19.time_series_p{partition_date}_utla AS ts
                               JOIN covid19.release_reference AS rr ON rr.id = release_id
                               JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                               JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
                  )
                  UNION
                  (
                      SELECT *
                      FROM covid19.time_series_p{partition_date}_ltla AS ts
                               JOIN covid19.release_reference AS rr ON rr.id = release_id
                               JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                               JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
                  )
              ) AS ts
         WHERE date > (DATE(:datestamp) - INTERVAL '20 days')
           AND metric = 'cumVaccinationFirstDoseUptakeByPublishDatePercentage'
           AND (payload ->> 'value') NOTNULL
         GROUP BY area_type, area_code
     ) as first
         JOIN (
    SELECT area_type,
           area_code,
           MAX(date)                        AS date,
           MAX((payload -> 'value')::FLOAT) AS second_dose
    FROM (
             SELECT *
             FROM covid19.time_series_p{partition_date}_other AS tm
                      JOIN covid19.release_reference AS rr ON rr.id = release_id
                      JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                      JOIN covid19.area_reference AS ar ON ar.id = tm.area_id
             UNION
             (
                 SELECT *
                 FROM covid19.time_series_p{partition_date}_utla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
             )
             UNION
             (
                 SELECT *
                 FROM covid19.time_series_p{partition_date}_ltla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
             )
         ) AS ts
    WHERE date > ( DATE(:datestamp) - INTERVAL '20 days' )
      AND metric = 'cumVaccinationSecondDoseUptakeByPublishDatePercentage'
      AND (payload ->> 'value') NOTNULL
    GROUP BY area_type, area_code
) AS second ON first.date = second.date AND first.area_code = second.area_code
 JOIN (
    SELECT area_type,
           area_code,
           MAX(date)                        AS date,
           MAX((payload -> 'value')::FLOAT) AS third_dose
    FROM (
             SELECT *
             FROM covid19.time_series_p{partition_date}_other AS tm
                      JOIN covid19.release_reference AS rr ON rr.id = release_id
                      JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                      JOIN covid19.area_reference AS ar ON ar.id = tm.area_id
             UNION
             (
                 SELECT *
                 FROM covid19.time_series_p{partition_date}_utla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
             )
             UNION
             (
                 SELECT *
                 FROM covid19.time_series_p{partition_date}_ltla AS ts
                          JOIN covid19.release_reference AS rr ON rr.id = release_id
                          JOIN covid19.metric_reference AS mr ON mr.id = metric_id
                          JOIN covid19.area_reference AS ar ON ar.id = ts.area_id
             )
         ) AS ts
    WHERE date > ( DATE(:datestamp) - INTERVAL '20 days' )
      AND metric = 'cumVaccinationThirdInjectionUptakeByPublishDatePercentage'
      AND (payload ->> 'value') NOTNULL
    GROUP BY area_type, area_code
) AS third ON first.date = third.date AND first.area_code = third.area_code
GROUP BY first.area_type, first.area_code;\
"""


TIMESRIES_QUERY = """\
SELECT
     date                           AS "date",
     (payload ->> 'value')::NUMERIC AS "value"
FROM covid19.time_series_p{partition} AS main
JOIN covid19.release_reference AS rr ON rr.id = release_id
JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
JOIN covid19.area_reference    AS ar ON ar.id = main.area_id
WHERE
      partition_id = :partition_id
  AND area_type = 'overview'
  AND date > ( NOW() - INTERVAL '6 months')
  AND metric = :metric
ORDER BY date DESC;\
"""


LATEST_CHANGE_QUERY = """\
SELECT
     metric,
     date                        AS "date",
     (payload -> 'value')::FLOAT AS "value"
FROM covid19.time_series_p{partition} AS ts
JOIN covid19.release_reference AS rr ON rr.id = release_id
JOIN covid19.metric_reference  AS mr ON mr.id = metric_id
JOIN covid19.area_reference    AS ar ON ar.id = ts.area_id
WHERE
      partition_id = :partition_id
  AND area_type = 'overview'
  AND date > ( DATE( :datestamp ) - INTERVAL '30 days' )
  AND metric = :metric
ORDER BY date DESC
OFFSET 0
FETCH FIRST 1 ROW ONLY;\
"""
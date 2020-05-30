from app import db
from datetime import datetime, timedelta

def _execute_query(query, data=None):
    with db.engine.connect() as con:
        if data is None:
            return list(con.execute(query))
        return list(con.execute(query, data))

def get_scans_by_date(age=14):
    query = """
        SELECT
            COUNT(*) as count, provider, DATE(scan_date) AS date
        FROM
            tbl_provider_scans
        WHERE
            DATEDIFF(NOW(), scan_date) < %s
        GROUP BY
            date, provider
        ORDER BY
            date
    """
    return _execute_query(query, (age, ))

def get_latest_scan_ids():
    query = "SELECT * FROM tmp_latest_scan_ids"
    return [d['scan_id'] for d in _execute_query(query)]

def get_latest_offers(set_number):
    query = """
        SELECT
            *,
            (
                100 -(
                    tbl_provider_scans.price
                ) /(blp.qty_avg_price / 100)
            ) AS save_in_percentage_bl,
            (
                100 -(
                    tbl_provider_scans.price
                ) /(tbl_sets.ch_price / 100)
            ) AS save_in_percentage_lp
        FROM
            tbl_provider_scans
        JOIN tbl_sets ON tbl_sets.set_number = tbl_provider_scans.set_number
        LEFT JOIN tmp_newest_bricklink_prices AS blp
        ON
            blp.set_number = tbl_provider_scans.set_number AND blp.product_condition = 'new'
		JOIN tmp_latest_scan_ids AS sid USING(scan_id)
        WHERE 
            tbl_provider_scans.set_number = %s
        ORDER BY
            price
    """
    return _execute_query(query, (set_number, ))

def get_sets_currently_on_market():
    query = """
        SELECT
            *,
            (
                (
                    blp.qty_avg_price /(tbl_sets.ch_price / 100)
                ) - 100
            ) AS difference
        FROM
            tbl_provider_scans
        RIGHT JOIN tbl_sets USING(set_number)
        JOIN tmp_newest_bricklink_prices AS blp
        ON
            blp.set_number = tbl_provider_scans.set_number AND
            blp.product_condition = 'new'
        JOIN tmp_latest_scan_ids USING(scan_id)
        GROUP BY
            tbl_provider_scans.set_number
        ORDER BY
            tbl_sets.theme, tbl_sets.year
    """
    return _execute_query(query)

def get_sets_on_market_unique(theme='%'):
    query = """
        SELECT
            *
        FROM
            tbl_provider_scans
        RIGHT JOIN tbl_sets USING(set_number)
        JOIN tmp_latest_scan_ids USING(scan_id)
        WHERE
            tbl_sets.theme LIKE %s
        GROUP BY
            tbl_provider_scans.set_number
        ORDER BY
            tbl_sets.year
        DESC
    """
    return _execute_query(query, (theme, ))

def get_set_information(set_number='%'):
    query = """
        SELECT
            tbl_provider_scans.*,
            tbl_sets.*,
            blp.qty_avg_price,
            (
                (
                    blp.qty_avg_price /(tbl_sets.ch_price / 100)
                ) - 100
            ) AS difference
        FROM
            tbl_sets
        LEFT JOIN tbl_provider_scans USING(set_number)
        LEFT JOIN tmp_newest_bricklink_prices AS blp
        ON
            blp.set_number = tbl_sets.set_number AND
            blp.product_condition = 'new'
        LEFT JOIN tmp_latest_scan_ids USING(scan_id)
        WHERE
            tbl_sets.set_number LIKE %s
        GROUP BY
            tbl_sets.set_number
        ORDER BY
            tbl_sets.set_number
        DESC
    """
    return _execute_query(query, (set_number, ))

def get_new_listings():
    query = """
        SELECT
            *
        FROM
            tbl_provider_scans
        INNER JOIN(
            SELECT
                set_number,
                MIN(scan_date) AS scan_date
            FROM
                tbl_provider_scans
            GROUP BY
                set_number
        ) AS MAX USING(set_number, scan_date)
        LEFT JOIN tbl_sets USING(set_number)
        WHERE
            scan_date > NOW() - INTERVAL 4 WEEK
        ORDER BY
            scan_date
        DESC
    """
    return _execute_query(query)         

def get_provider_deals(bl_treshold=0, lp_treshold=40, query_pattern='%'):
    query = """
        SELECT
            *,
            (
                100 -(
                    tbl_provider_scans.price /(blp.qty_avg_price / 100)
                )
            ) AS save_in_percentage_bl,
            (
                100 -(
                    tbl_provider_scans.price /(tbl_sets.ch_price / 100)
                )
            ) AS save_in_percentage_lp
        FROM
            tbl_provider_scans
        JOIN tmp_newest_bricklink_prices AS blp
        ON
            blp.set_number = tbl_provider_scans.set_number AND
            blp.product_condition = 'new'
        LEFT JOIN tbl_sets
        ON
            tbl_sets.set_number = tbl_provider_scans.set_number
        JOIN tmp_latest_scan_ids USING(scan_id)
        WHERE
            blp.qty_avg_price > 0 AND
            tbl_sets.name IS NOT NULL AND 
            (
                (
                    100 -(
                        tbl_provider_scans.price /(blp.qty_avg_price / 100)
                    )
                ) > %s OR
                (
                    100 -(
                        tbl_provider_scans.price /(tbl_sets.ch_price / 100)
                    )
                ) > %s
            ) AND (
                tbl_provider_scans.set_number LIKE %s OR
                tbl_provider_scans.title LIKE %s OR
                tbl_sets.name LIKE %s OR
                tbl_sets.theme LIKE %s OR
                tbl_sets.subtheme LIKE %s
            ) 
        GROUP BY
            tbl_provider_scans.set_number,
            tbl_provider_scans.provider
        ORDER BY
            save_in_percentage_bl
        DESC
    """
    return _execute_query(query, (bl_treshold, lp_treshold, query_pattern, query_pattern, query_pattern, query_pattern, query_pattern))

def get_auction_deals():
    query = """
        SELECT
            *,
            (
                tbl_auction_scans.auction_price + tbl_auction_scans.shipping_price
            ) AS price,
            blp.qty_avg_price,
            (
                100 -(
                    tbl_auction_scans.auction_price + tbl_auction_scans.shipping_price
                ) /(blp.qty_avg_price / 100)
            ) AS save_in_percentage
        FROM
            tbl_auction_scans
        JOIN tbl_sets USING(set_number)
        JOIN tmp_newest_bricklink_prices AS blp
        ON
            tbl_auction_scans.set_number = blp.set_number AND blp.product_condition = tbl_auction_scans.product_condition
        WHERE
            blp.qty_avg_price > 0 AND
            tbl_auction_scans.has_auction = 1 AND
            tbl_auction_scans.end_date > NOW() AND
            DATEDIFF(tbl_auction_scans.end_date,NOW()) < 1
        ORDER BY
            save_in_percentage
        DESC
    """
    return _execute_query(query)

def get_buy_now_deals(after=datetime.now()+timedelta(hours=-296)):
    query = """
        SELECT
            *,
            (
                tbl_auction_scans.buy_now_price + tbl_auction_scans.shipping_price
            ) AS price,
            blp.qty_avg_price,
            (
                100 -(
                    tbl_auction_scans.buy_now_price + tbl_auction_scans.shipping_price
                ) /(blp.qty_avg_price / 100)
            ) AS save_in_percentage,
            tbl_auction_scans.scan_date
        FROM
            tbl_auction_scans
        JOIN tbl_sets USING(set_number)
        JOIN tmp_newest_bricklink_prices AS blp USING(set_number, product_condition)
        WHERE
            tbl_auction_scans.buy_now_price IS NOT NULL AND
            blp.qty_avg_price > 0 AND
            tbl_auction_scans.has_buy_now = 1 AND
            tbl_auction_scans.end_date > NOW() AND
            tbl_auction_scans.scan_date > %s
        GROUP BY
            tbl_auction_scans.url
        ORDER BY
            save_in_percentage
        DESC
    """
    return _execute_query(query, (after, ))

def get_market_statistics_for_sets():
    query = """
        SELECT
            *,
            (
                (
                    blp.qty_avg_price /(tbl_sets.us_price / 100)
                ) -100
            ) AS difference_in_percent
        FROM
            tbl_sets
        JOIN tmp_newest_bricklink_prices AS blp
        ON
            tbl_sets.set_number = blp.set_number AND product_condition = 'new'
        WHERE
            tbl_sets.theme LIKE '%%' AND
            (tbl_sets.subtheme LIKE '%%' OR tbl_sets.subtheme IS NULL) AND
            tbl_sets.us_price IS NOT NULL AND
            blp.qty_avg_price > 0
        ORDER BY
            difference_in_percent
        DESC
    """
    return _execute_query(query)

if __name__ == '__main__':
    get_latest_offers(70424)
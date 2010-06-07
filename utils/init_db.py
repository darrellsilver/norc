#!/usr/bin/python

###############################
#
# Set up initial data for Perpetually & Taskmaster
#
#
#Run these exact steps to go from no tables to full setup:
# 1) python permalink/manage.py syncdb --noinput
# 2) python taskmaster/manage.py syncdb --noinput
# 3) python bin/init_db.py --init [--setup_crawls | --run_crawls]
#
#Fast & all at once, with no data:
# python permalink/manage.py syncdb --noinput; python taskmaster/manage.py syncdb --noinput; python bin/init_db --init --setup_crawls
#
#Now, turn on the archivin':
# * tmsd --region QA
# * sqsd --queue SQSArchiveRequest-NORMAL --max 1
#
#TODO call syncdb for permalink & taskmaster here instead of expecting it
#TODO add a 'clear' option to clear all tables instead of
#
#Monitor what's going on:
# * See what's enqueued: sqsctl
# * See running daemons: tmsdctl --status
#
#Generally helpful things:
#To drop all tables in DB:
# mysqldump -u qa_perpetually -pperpetua33y --add-drop-table --no-data qa_perpetually | grep DROP | mysql -u qa_perpetually -pperpetua33y qa_perpetually
#To load an SQL file into MySQL:
# mysql -u qa_permalink -p perpetually_flash < assets_not_src/post.init_db.dump/mysqldump.sql
#
###############################


wsj_login_instructions = """
CREATE TABLE moz_cookies (id INTEGER PRIMARY KEY, name TEXT, value TEXT, host TEXT, path TEXT,expiry INTEGER, lastAccessed INTEGER, isSecure INTEGER, isHttpOnly INTEGER);
INSERT INTO "moz_cookies" VALUES(1265240393557599,'PREF','ID=b232ed187e1df700:TM=1265240393:LM=1265240393:S=Yl3JsmRcAbjaun4Q','.google.com','/',1328312393,1265240473213449,0,0);
INSERT INTO "moz_cookies" VALUES(1265240397179772,'BBC-UID','242b36baf01954bd2b5a12b0c1127174b4f3e9c7f040c12f7239b6129d0ab4aa0Mozilla%2f5%2e0%20%28X11%3b%20U%3b%20Linux%20x86%5f64%3b%20en%2dUS%3b%20rv%3a1%2e9%2e2%2e2pre%29%20Gecko%2f20100203%20Namoroka%2f3%2e6%2e2pre','.bbc.co.uk','/',1296776397,1265240397180269,0,0);
INSERT INTO "moz_cookies" VALUES(1265240457426810,'djcs_route','aa91ec32-5ad6-4a5e-a049-067142831aa4','.wsj.com','/',1580600457,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458368919,'id','ce132cd23000062||t=1265240458|et=730|cs=j-xuz4_x','.doubleclick.net','/',1328312458,1265242335286403,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458519953,'pluto2','757796801731','.fastclick.net','/',1328312458,1265241190207060,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458520366,'lyc','AgAAAAT4CWpLACAAAKJgBYAAAWAvgAdAAOAFFwEAAA==','.fastclick.net','/',1328313190,1265241190510339,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458520604,'pluto','757796801731','.fastclick.net','/',1328313190,1265241190510485,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458891504,'s_vnum','1267832458891%26vn%3D1','.wsj.com','/',1267832458,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458891732,'s_invisit','true','.wsj.com','/',1265242990,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265240458891904,'s_dbfe','1265240458891','.wsj.com','/',1359848458,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459456977,'s_vi','[CS]v1|25B504C5851D2AE0-4000012920688E7C[CE]','.dowjoneson.com','/',1422920459,1265241177054480,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459710066,'IXAIBanners1817','159239,160340,159239,159239,159058,159058,159058','.insightexpressai.com','/',1422964800,1265242152088306,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459710237,'IXAIBannerCounter159239','4','.insightexpressai.com','/',1422964800,1265242151987736,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459710308,'IXAIFirstHit1817','2%2f3%2f2010+6%3a36%3a25+PM','.insightexpressai.com','/',1422964801,1265242151987736,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459710390,'IXAILastHit1817','2%2f3%2f2010+6%3a35%3a19+PM','.insightexpressai.com','/',1422964800,1265242152089058,0,0);
INSERT INTO "moz_cookies" VALUES(1265240459710466,'IXAICampaignCounter1817','7','.insightexpressai.com','/',1422964800,1265242152089331,0,0);
INSERT INTO "moz_cookies" VALUES(1265240460080135,'LO','00GO6P6Fk00000f50031','.opt.fimserve.com','/',1273103591,1265241191515354,0,0);
INSERT INTO "moz_cookies" VALUES(1265240460080297,'UI','20d76d2522c673a10e|f..9.f.f.f.f@@f@@f@@f@@f@@f@@f','.opt.fimserve.com','/',1580600461,1265241191105239,0,0);
INSERT INTO "moz_cookies" VALUES(1265240515904083,'DJCOOKIE','','.wsj.com','/',18446744073708,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265240517000718,'_loomiaUTrack','88315_563114','.loomia.com','/',1394840517,1265240517000718,0,0);
INSERT INTO "moz_cookies" VALUES(1265240517174939,'IXAIBannerCounter160340','1','.insightexpressai.com','/',1422964800,1265242151987736,0,0);
INSERT INTO "moz_cookies" VALUES(1265240517524155,'S','pgt35u-13604-1265240517448-4f','.apmebf.com','/',1328312517,1265240517524155,0,0);
INSERT INTO "moz_cookies" VALUES(1265240517629095,'svid','417594586509','.mediaplex.com','/',1359870391,1265240517629095,0,0);
INSERT INTO "moz_cookies" VALUES(1265240517629487,'mojo3','14302:1281','.mediaplex.com','/',1328247991,1265240517629487,0,0);
INSERT INTO "moz_cookies" VALUES(1265240681984076,'rsi_ct','2010_2_3:3','commerce.wsj.com','/',1265327577,1265241177056929,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188628671,'djcs_demo','VjE6O2c9TQ%3D%3D','.wsj.com','/',1267833188,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188629017,'user_type','subscribed','.wsj.com','/',1580601188,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188629248,'TR','101051100051054053056099045052053054099045052098100102045098097101048045099051100099051100050097102051051048','.wsj.com','/',1580601188,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188629483,'REMOTE_USER','e3d3658c-456c-4bdf-bae0-c3dc3d2af330','.wsj.com','/',1580601188,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188629719,'djcs_auto','M1265231024%2Fgl6peMXzlQG1J5Thd%2BuCz2SNYpgA%2BSL3JpyAPdA8eCQChSYCrc2jRUbPlloWIFrqN1OmLXadcenHQoLJh0CRHwK6fXTa7tgx9MsrE4A6FHYyGQYR6lIpyZSfsRk75Xmb%2Fq0%2B3QX4Si16sIVbb1v3Ceqwxj1tKVWOO6%2BTfA3jwC2W42QxJ5p7pk08KCiD980xEO0m2Jn2%2F3bIjQ1PR%2BvJdA%3D%3DG','.wsj.com','/',1422921188,1265242331987523,0,1);
INSERT INTO "moz_cookies" VALUES(1265241188630179,'djcs_perm','M1265231024%2F7o1BEHiiNXvYWdrxCMIBBGKEI6ws2vuomBvbZXZykSbhUswAv5UWj9YpfIZLSZ%2BcrGu0syKuHHOP4SkWMhJb1RyNcxGhRKeg78r%2Fk7vjlZ6Ivy5TtWZErKObZPYcBWXPe5e3y8WpAMCv7FuLjgz0AwBzB6yREhbj3Lek9IHOddKY4mG3VIER88NSrsdPmf8nJF2bYS718zu4cnPyDwVf8OAMfWhV9bLAYZAwEJyOs0JWiNlGLpuCKu9anQjSILLO5cM5UThw6Ifbd%2BXSyrET5hl0L4Um8go7yQPt%2BqEfDgdTQWKMbDs4AuUsYl8e36ylo5mGWLnu%2FbJTxTEXT44JJvZG8wA6H%2BT0x%2BlGRFBHW3ZnMXVJFz%2FxFhfnAAk8kDXTG','.wsj.com','/',1422921188,1265242331987523,0,1);
INSERT INTO "moz_cookies" VALUES(1265241188760492,'djcs_demo','VjE6O2c9TQ%3D%3D','.barrons.com','/',1267833188,1265241188760492,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188760904,'user_type','subscribed','.barrons.com','/',1580601188,1265241188760904,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188761145,'TR','101051100051054053056099045052053054099045052098100102045098097101048045099051100099051100050097102051051048','.barrons.com','/',1580601188,1265241188761145,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188761420,'REMOTE_USER','e3d3658c-456c-4bdf-bae0-c3dc3d2af330','.barrons.com','/',1580601188,1265241188761420,0,0);
INSERT INTO "moz_cookies" VALUES(1265241188761657,'djcs_auto','M1265231024%2Fwau2%2Fa39lHcMn1mt9%2BiQjLZsZ1J2eW88wqN6Ah4UkuJi1WxSFfr6cL5DDFPrG1F2JFqoVoaPvbqMXZLppkZMBLUOw%2BuGDOqfo2Vk8AEEt2cy3NnlcoXW2Ob4QqEXUy7VIbuoEpyDnFRC1wN1qfEy3fpqrGUiipCIynQJHoew3%2FGmuHB%2BdQPcCKr2UK%2B4uCDf0F%2BtIs0O%2Bg5EDu%2FzKtVTYA%3D%3DG','.barrons.com','/',1422921188,1265241188761657,0,1);
INSERT INTO "moz_cookies" VALUES(1265241188762079,'djcs_perm','M1265231024%2FzdxDGSkGxu2lpn8h08QqS48sRBd77UdZArCq9N6B7vG93T9I597XJpasm1Rdkntory2d2anAuzxJLnVpdADGjnRThC1SYeHYAGwMWYZhpZ5cRZlwWnq8LBRHbP09TCk0AFLrl2hmFwKceKbIcKxeiS6b0BvH1GZtbRefqIBURt%2Fd0KKjH00UoGg8nJafXsMkUJEAgRNYOIuQGAh0f7NrlFIJTQKYFyXGYfFvGK%2FED1aJCBXEtoC4d5TOZFTfMtxkGfJC36wvAhq89mF7NDROG6%2BCgglsLzwK3%2F0pNmbDbeaXaNZf9MaqPmj1fgn6DDttd7HRKWeB2l1h%2F3%2FT3CNoKuhuDouIzGPQaGVoHxsbG9jxMxu2WWa44bLQCoH5i3%2BbG','.barrons.com','/',1422921188,1265241188762079,0,1);
INSERT INTO "moz_cookies" VALUES(1265241190618258,'CMC','top','.wsj.com','/',1265327590,1265242331987523,0,0);
INSERT INTO "moz_cookies" VALUES(1265241190885025,'msgCount','-1','.wsj.com','/',1265241490,1265241431167391,0,0);
INSERT INTO "moz_cookies" VALUES(1265241191388843,'IXAIBannerCounter159058','3','.insightexpressai.com','/',1422964800,1265242152088756,0,0);

"""

import os, sys
import datetime
from permalink import api
from optparse import OptionParser
from django.contrib.auth.models import User

from permalink.core import models as core

from utils import log
log = log.Log()

def init_superuser():
    assert User.objects.all().count() == 0, "User(s) already exist in the DB!"
    
    # username=1@1.com, password=1
    user = User.objects.create_user('1@1.com', '1@1.com', '1')
    user.is_staff = True
    user.is_superuser = True
    user.save()
    assert user.id == 1, "Created superuser but id is not 1! \
Are there users already defined in the DB?"
    return user

def _init_payment_plan(sku, name, price, max_mycrawls, max_gb, max_pages):
    from access.models import PaymentPlan
    payment_plan = PaymentPlan(sku=sku, name=name, price=price
        , current_max_mycrawls=max_mycrawls
        , current_max_gb=max_gb, max_pages_month=max_pages)
    payment_plan.save()
    return payment_plan

def init_permalink(admin_user):
    log.info("Initializing permalink")
    
    from access.models import PaymentPlan, PurchasedPlan
    from access import views as access_views
    from permalink.archiver.storage import StorageFacilityRecord
    
    _init_payment_plan(access_views.EXPENSIVE_SKU, "Large", 49.0
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED, 600)
    _init_payment_plan(access_views.MEDIUM_SKU, "Medium", 19.0
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED, 200)
    payment_plan = _init_payment_plan(access_views.FREE_SKU, "Free", 0
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED
        , PaymentPlan.UNLIMITED_MYCRAWLS_ALLOWED, 20)
    
    purchased_plan = PurchasedPlan.create(admin_user, payment_plan, "QA_ORDER_ID")
    purchased_plan.save()# TODO This shouldn't be necessary
    
    storage_facility_fs = StorageFacilityRecord(name="FileSystemStorageFacility"
        , started=datetime.datetime.utcnow())
    storage_facility_fs.save()
    storage_facility_pfs = StorageFacilityRecord(name="PonyFileSystemStorageFacility"
        , started=datetime.datetime.utcnow())
    storage_facility_pfs.save()
    storage_facility_s3 = StorageFacilityRecord(name="S3StorageFacility"
        , started=datetime.datetime.utcnow())
    storage_facility_s3.save()
    storage_facility_ps3 = StorageFacilityRecord(name="PonyS3StorageFacility"
        , started=datetime.datetime.utcnow())
    storage_facility_ps3.save()

    data_source = core.DataSource(name="DIRECT")
    data_source.save()
    log.info("Success! permalink initted")

def _create_ResourceRegion(name):
    from taskmaster.core.models import ResourceRegion
    from taskmaster import settings
    from taskmaster.core.models import ResourceRegion
    
    rr = ResourceRegion.create(name)
    log_dir = os.path.join(settings.TMS_LOG_DIR, name)
    if not os.path.exists(log_dir):
        log.error("Log dir for '%s' should exist at '%s' but doesn't!" 
            % (name, log_dir))
    return rr

def init_taskmaster():
    log.info("Initializing taskmaster")
    
    from taskmaster.core.models import Job, Iteration
    from taskmaster.core.models import Resource, RegionResourceRelationship
    from taskmaster.core.models import TaskClassImplementation
    
    j = Job(name="MANAGE_ARCHIVE", description="All perpetually repeating tasks go here")
    j.save()
    
    i = Iteration.create(j, Iteration.ITER_TYPE_PERSISTENT)
    
    _create_ResourceRegion("SQSArchiveRequest-NORMAL")
    _create_ResourceRegion("SQSArchiveRequest-INSTANT")
    _create_ResourceRegion("SQSBrowserPublish-v0-4")
    _create_ResourceRegion("SQSPublishRecord-v0-4")
    resource_region_sqs_qa = _create_ResourceRegion("QA")
        
    resource = Resource.create("DATABASE_CONNECTION")
    
    # SQS Regions don't have RegionResourceRelationships; 
    # they get only a --max at run time
    rrr = RegionResourceRelationship.create(resource_region_sqs_qa, resource, 100)
    
    tci = TaskClassImplementation(status=TaskClassImplementation.STATUS_ACTIVE
        , library_name="permalink.tms_impl.models", class_name="CrawlSchedule")
    tci.save()
    
    log.info("Success! taskmaster initted")

def run_crawl(my_crawl):
    no_queue_crawl = my_crawl.start_crawl()
    for surl in my_crawl.get_seed_urls():
        log.info("'--noqueue' specified. Archiving '%s' now." % (surl.get_url()))
        api.add_URL(surl.get_url(), '~cmd_line', no_queue_crawl \
        , surl.get_include_in_listing() \
        , surl.get_content_archiver(), False)

def add_page(user, schedule_name, url, run_now
    , login_instructions=False, privacy_level=core.MyCrawls.PRIVACY_PRIVATE):
    log.info("Adding page '%s' on schedule %s" % (url, schedule_name))
    
    from permalink.tms_impl import models as tms_permalink
    
    ff = core.NDepthCrawler.create(default_max_crawl_depth=0
        , apply_robots_for_embedded=False, apply_robots_for_non_embedded=True)
    cs = tms_permalink.CrawlSchedule.create_predefined(schedule_name)
    data_source = core.DataSource.get('DIRECT')
    crawl_name = url[0:128]
    (my_crawl, is_new) = core.MyCrawls.get_or_create(user, crawl_name
        , privacy_level
        , core.MyCrawls.ARCHIVE_LEVEL_FULL
        , core.MyCrawls.PROCESSING_LEVEL_NORMAL
        , 500, data_source, ff, task=cs)

    if not is_new:
        raise Exception("Cannot add_page(); crawl by name '%s' already exists!" % (crawl_name))

    core.SeedURL.create(my_crawl, url, None, True)
    if login_instructions:
        lm = core.LoginMethod(login_instructions = login_instructions)
        lm.save()
        my_crawl.login_method = lm
        my_crawl.save()
        
    if run_now:
        run_crawl(my_crawl)

def init_static():
    user = init_superuser()
    init_permalink(user)
    init_taskmaster()
    return user

def init_sites(user, run_now):
    # This list cannot have duplicates!
    add_page(user, "HALFHOURLY", "http://www.msnbc.msn.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.msn.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.aol.com/", run_now
        , privacy_level=core.MyCrawls.PRIVACY_PUBLIC)
    add_page(user, "HALFHOURLY", "http://www.washingtonpost.com/", run_now)
    add_page(user, "HALFHOURLY", "http://arabic.cnn.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.huffingtonpost.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.newegg.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.nytimes.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.myspace.com/katspack", run_now)
    add_page(user, "HALFHOURLY", "http://slashdot.org/", run_now)
    add_page(user, "HALFHOURLY", "http://www.weather.com/", run_now)
    add_page(user, "HALFHOURLY", "http://www.sina.com.cn/", run_now)
    add_page(user, "HALFHOURLY", "http://www.amazon.com/PlayStation-3-Games/b/ref=amb_link_82697231_6?ie=UTF8&node=14210751&pf_rd_m=ATVPDKIKX0DER&pf_rd_s=center-2&pf_rd_r=0AG7CTR5J6VYC9VDVNB6&pf_rd_t=101&pf_rd_p=481684871&pf_rd_i=507846", run_now)
    add_page(user, "HALFHOURLY", "http://wsj.com/", run_now
        , login_instructions=wsj_login_instructions)
    add_page(user, "HALFHOURLY", "http://cn.wsj.com/", run_now)
    add_page(user, "HALFHOURLY", "http://onion.com/", run_now)
    add_page(user, "HALFHOURLY", "http://citrix.com/", run_now)
    add_page(user, "HALFHOURLY", "http://independent.co.uk", run_now)
    add_page(user, "HALFHOURLY", "http://lemonde.fr/", run_now)
    add_page(user, "HALFHOURLY", "http://perpetually.com/", run_now)
    add_page(user, "HALFHOURLY", "http://adobe.com/", run_now)

def main():
    parser = OptionParser("%prog [--init] [--setup_crawls | --run_crawls]")
    parser.add_option("--init", action="store_true"
        , help="setup static data to the DBs")
    parser.add_option("--setup_crawls", action="store_true"
        , help="setup recurring tasks for a nice cross section of random sites")
    parser.add_option("--run_crawls", action="store_true"
        , help="setup & run recurring tasks for a nice cross section of random sites")
    (options, args) = parser.parse_args()
    
    if options.setup_crawls and options.run_crawls:
        sys.exit(parser.get_usage())
    
    if options.init:
        user = init_static()
    else:
        user = User.objects.get(username="1@1.com")
    
    if options.setup_crawls:
        init_sites(user, False)
    elif options.run_crawls:
        init_sites(user, True)


if __name__ == '__main__':
    main()

#

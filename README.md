# dspace-stats-db 

Supplemental scripting to import dspace 7 api usage stats into a postgresql instnace. Using foreign data wrapper (fdw), these tables can be imported as foreign tables in dspace database allowing easier reporting for file view and downloads with all relevant metadata and grouping by collections/communities. 

Each script runs as a cronjob and data is updated or inserted depending existance of uuid. 

SQL Examples

```
select handle,uuid, "views", downloads, title, filename, i.owning_collection
from api_filedownload_stats afs 
join api_itemview_stats ais on ais.item_id = afs.item_id 
join item i on i.uuid = ais.item_id 
join handle h on h.resource_id = i.uuid
where i.owning_collection ='7603db13-cd5d-46ce-abd3-05c6f3b41b0b'
order by handle 
```
```
select sum("views")
from api_itemview_stats ais 
join item i on i.uuid = ais.item_id 
join handle h on h.resource_id = i.uuid
where i.owning_collection ='7603db13-cd5d-46ce-abd3-05c6f3b41b0b'
```
```
select sum("views")
from api_itemview_stats ais 
```
```
select sum("downloads")
from api_filedownload_stats afs 
```
-- rollup download totals by handle, title, and filename. 
```
select handle, title, afs.filename,sum(downloads) as downloads
from api_filedownload_stats afs 
join api_itemview_stats ais on ais.item_id = afs.item_id 
join item i on i.uuid = ais.item_id 
join handle h on h.resource_id = i.uuid
-- where i.owning_collection ='7603db13-cd5d-46ce-abd3-05c6f3b41b0b'
group by rollup (handle, title, afs.filename)
--group by ais.item_id
order by handle
```
-- could just group by handle,title, sum 
```
select handle, title, sum("views") as views, sum(downloads) as downloads
from api_filedownload_stats afs 
join api_itemview_stats ais on ais.item_id = afs.item_id 
join item i on i.uuid = ais.item_id 
join handle h on h.resource_id = i.uuid
where i.owning_collection ='7603db13-cd5d-46ce-abd3-05c6f3b41b0b'
group by (handle, title)
-- group by ais.item_id
order by title
```

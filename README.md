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

-- fun one that outputs file downloads and several values from metadatavalue table. 
```
SELECT handle, title,  
       string_agg(distinct m.text_value, '; ') as "author(s)",
       string_agg(DISTINCT mc.text_value, ', ') as "Collection",
       sum_downloads.total_downloads
FROM (
    SELECT item_id, SUM(downloads) as total_downloads
    FROM api_filedownload_stats
    GROUP BY item_id
) as sum_downloads
JOIN api_itemview_stats ais ON ais.item_id = sum_downloads.item_id 
JOIN metadatavalue m ON ais.item_id = m.dspace_object_id AND m.metadata_field_id = 3
JOIN item i ON i.uuid = m.dspace_object_id 
JOIN handle h ON h.resource_id = i.uuid
LEFT JOIN community2collection c2c ON i.owning_collection = c2c.collection_id
LEFT JOIN metadatavalue mc ON c2c.collection_id = mc.dspace_object_id AND mc.metadata_field_id = 64
WHERE c2c.community_id = 'ea995a3c-462c-41ce-b455-2daa65e598cb'
GROUP BY handle, title, sum_downloads.total_downloads
ORDER BY "Collection";
```

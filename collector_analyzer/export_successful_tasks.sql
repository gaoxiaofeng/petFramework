select t.task_id, t.template_id, t.status,p.template_arguments, 
extract(second from (t.stop_time - t.start_time)) + extract(minute from (t.stop_time - t.start_time))*60 + extract(hour from (t.stop_time - t.start_time))*60*60 + extract(day from (t.stop_time - t.start_time))*60*60*24  as running_cost,
extract(second from (t.stop_time - t.create_time)) + extract(minute from (t.stop_time - t.create_time))*60 + extract(hour from (t.stop_time - t.create_time))*60*60 + extract(day from (t.stop_time - t.start_time))*60*60*24  as total_cost,
t.failed_reason, t.RESULT_FILE_ADDRESS, t.start_time,t.stop_time
from task_info t join plan_info p on t.plan_id = p.plan_id 
where  t.create_time >= to_date('{scenario_start_time}','yyyy-mm-dd hh24:mi:ss') and t.create_time <= to_date('{scenario_stop_time}','yyyy-mm-dd hh24:mi:ss')
and (t.status in (3)  or (t.status in (5) and t.failed_reason is null))
order by task_id  desc;
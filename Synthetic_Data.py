import pandas as pd
import numpy as np
from collections import defaultdict

def assign_job_categories(job_names):
    categories = ['short', 'medium', 'long', 'very_long']
    probabilities = [0.7, 0.25, 0.04, 0.01]
    return {job: np.random.choice(categories, p=probabilities) for job in job_names}

def assign_upgrade_impact(job_names):
    impacts = ['improved', 'regressed', 'unchanged']
    probabilities = [0.5, 0.2, 0.3]
    return {job: np.random.choice(impacts, p=probabilities) for job in job_names}

def assign_schedule(job_names):
    schedules = ['15min', 'daily', 'monthly', 'unscheduled']
    probabilities = [0.6, 0.2, 0.05, 0.15]
    return {job: np.random.choice(schedules, p=probabilities) for job in job_names}

def generate_duration(category, is_after_upgrade, impact, schedule):
    base_duration = {
        'short': (1, 120),
        'medium': (120, 900),  # Changed upper limit to 15 minutes
        'long': (900, 86400),
        'very_long': (86400, 259200)
    }[category]
    
    if schedule == '15min':
        max_duration = 900  # 15 minutes in seconds
    elif schedule == 'daily':
        max_duration = 86400  # 1 day in seconds
    elif schedule == 'monthly':
        max_duration = 259200  # 3 days in seconds
    else:  # unscheduled
        max_duration = 259200  # 3 days in seconds

    duration = min(np.random.randint(*base_duration), max_duration)
    
    if is_after_upgrade:
        if impact == 'improved':
            duration = int(duration * np.random.uniform(0.5, 0.9))
        elif impact == 'regressed':
            duration = int(duration * np.random.uniform(1.1, 1.5))
    
    return max(1, min(duration, max_duration))

n_samples = 1000000
job_names = [f'JOB_{i}' for i in range(1, 167)]
job_categories = assign_job_categories(job_names)
job_impacts = assign_upgrade_impact(job_names)
job_schedules = assign_schedule(job_names)

data = defaultdict(list)

start_date = pd.Timestamp('2023-09-01')
upgrade_date = pd.Timestamp('2024-05-19')
end_date = pd.Timestamp('2024-06-22')

total_days = (end_date - start_date).days
pre_upgrade_days = (upgrade_date - start_date).days
post_upgrade_days = (end_date - upgrade_date).days

n_samples_pre = int(n_samples * (pre_upgrade_days / total_days))
n_samples_post = n_samples - n_samples_pre

oprids = ['mcurtis', 'jdoe', 'asmith', 'bjohnson', 'ewilliams', 'scheduler']

for is_after_upgrade, n in [(False, n_samples_pre), (True, n_samples_post)]:
    for _ in range(n):
        job_name = np.random.choice(job_names)
        job_category = job_categories[job_name]
        job_impact = job_impacts[job_name]
        job_schedule = job_schedules[job_name]
        
        if is_after_upgrade:
            request_date = upgrade_date + pd.Timedelta(seconds=np.random.randint(0, post_upgrade_days * 86400))
        else:
            request_date = start_date + pd.Timedelta(seconds=np.random.randint(0, pre_upgrade_days * 86400))
        
        oprid = np.random.choice(oprids)
        
        if oprid == 'scheduler':
            if job_schedule == '15min':
                request_date = request_date.floor('15min')
            elif job_schedule == 'daily':
                request_date = request_date.floor('D')
            elif job_schedule == 'monthly':
                request_date = request_date.floor('D').replace(day=1)
        
        duration = generate_duration(job_category, is_after_upgrade, job_impact, job_schedule)
        
        # Generate begin time after request time
        begin_delay = np.random.randint(1, 300)  # 1 to 300 seconds delay
        begin_time = request_date + pd.Timedelta(seconds=begin_delay)
        
        # Generate end time after begin time
        end_time = begin_time + pd.Timedelta(seconds=duration)
        
        data['RQSTDTTM'].append(request_date)
        data['PRCSNAME'].append(job_name)
        data['SECONDS'].append(duration)
        data['MINUTES'].append(duration // 60)
        data['RUNSTATUSDESC'].append(np.random.choice(['Success', 'Error'], p=[0.9, 0.1]))
        data['PRCSINSTANCE'].append(np.random.randint(100000, 999999))
        data['OPRID'].append(oprid)
        data['RUNCNTLID'].append(np.random.choice(['EXTERNAL_PAYMENTS', 'INTERNAL_PAYMENTS']))
        data['IS_AFTER_UPGRADE'].append(is_after_upgrade)
        data['SCHEDULE'].append(job_schedule)
        data['BEGINDTTM'].append(begin_time)
        data['ENDDTTM'].append(end_time)

df = pd.DataFrame(data)

# Calculate actual duration based on BEGINDTTM and ENDDTTM
df['ACTUAL_DURATION'] = (df['ENDDTTM'] - df['BEGINDTTM']).dt.total_seconds() / 60

# Display overall statistics
print(df['ACTUAL_DURATION'].describe())

# Display job counts before and after upgrade
print(f"\nTotal jobs: {len(df)}")
print(f"Jobs before upgrade: {len(df[~df['IS_AFTER_UPGRADE']])} ({len(df[~df['IS_AFTER_UPGRADE']]) / len(df) * 100:.2f}%)")
print(f"Jobs after upgrade: {len(df[df['IS_AFTER_UPGRADE']])} ({len(df[df['IS_AFTER_UPGRADE']]) / len(df) * 100:.2f}%)")

# Display job duration distribution for scheduler and non-scheduler jobs
for oprid_type in ['scheduler', 'non-scheduler']:
    subset = df[df['OPRID'] == 'scheduler'] if oprid_type == 'scheduler' else df[df['OPRID'] != 'scheduler']
    print(f"\nJob duration distribution for {oprid_type} jobs:")
    print(f"Under 2 minutes: {(subset['ACTUAL_DURATION'] < 2).sum()} ({(subset['ACTUAL_DURATION'] < 2).sum() / len(subset) * 100:.2f}%)")
    print(f"2 to 15 minutes: {((subset['ACTUAL_DURATION'] >= 2) & (subset['ACTUAL_DURATION'] < 15)).sum()} ({((subset['ACTUAL_DURATION'] >= 2) & (subset['ACTUAL_DURATION'] < 15)).sum() / len(subset) * 100:.2f}%)")
    print(f"15 minutes to 4 hours: {((subset['ACTUAL_DURATION'] >= 15) & (subset['ACTUAL_DURATION'] < 240)).sum()} ({((subset['ACTUAL_DURATION'] >= 15) & (subset['ACTUAL_DURATION'] < 240)).sum() / len(subset) * 100:.2f}%)")
    print(f"4 hours to 1 day: {((subset['ACTUAL_DURATION'] >= 240) & (subset['ACTUAL_DURATION'] < 1440)).sum()} ({((subset['ACTUAL_DURATION'] >= 240) & (subset['ACTUAL_DURATION'] < 1440)).sum() / len(subset) * 100:.2f}%)")
    print(f"1 day to 3 days: {((subset['ACTUAL_DURATION'] >= 1440) & (subset['ACTUAL_DURATION'] <= 4320)).sum()} ({((subset['ACTUAL_DURATION'] >= 1440) & (subset['ACTUAL_DURATION'] <= 4320)).sum() / len(subset) * 100:.2f}%)")

# Display average duration for each job and schedule type
print("\nAverage duration for each job and schedule type:")
job_schedule_avg_duration = df.groupby(['PRCSNAME', 'SCHEDULE'])['ACTUAL_DURATION'].mean().sort_values(ascending=False)
for (job, schedule), avg_duration in job_schedule_avg_duration.items():
    category = job_categories[job]
    impact = job_impacts[job]
    print(f"{job}: {category} ({impact}, {schedule}) - Avg Duration: {avg_duration:.2f} min")

# Display distribution of schedule types
print("\nDistribution of schedule types:")
schedule_counts = df['SCHEDULE'].value_counts()
for schedule, count in schedule_counts.items():
    print(f"{schedule}: {count} ({count / len(df) * 100:.2f}%)")

# Verify timestamp consistency
print("\nVerifying timestamp consistency:")
print(f"Negative durations: {(df['ACTUAL_DURATION'] < 0).sum()}")
print(f"Begin time before request time: {(df['BEGINDTTM'] < df['RQSTDTTM']).sum()}")
print(f"End time before begin time: {(df['ENDDTTM'] < df['BEGINDTTM']).sum()}")

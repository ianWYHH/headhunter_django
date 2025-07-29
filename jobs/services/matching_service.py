from ..models import Job, Candidate


def find_matching_jobs(candidate: Candidate):
    """
    为指定候选人查找匹配的职位。

    匹配规则: 候选人的关键词与职位的关键词有任意一个重合即可。

    :param candidate: Candidate 实例
    :return: 一个包含匹配职位信息的字典列表
    """
    if not candidate.keywords:
        return []

    matching_jobs = []
    # 将候选人关键词转为集合，以提高匹配效率
    candidate_keywords_set = set(candidate.keywords)

    # 只对“进行中”或“待处理”的职位进行匹配
    active_jobs = Job.objects.filter(
        status__in=[Job.JobStatus.IN_PROGRESS, Job.JobStatus.PENDING]
    ).select_related('company')

    for job in active_jobs:
        if not job.keywords:
            continue

        job_keywords_set = set(job.keywords)

        # 计算两个关键词集合的交集
        matched_keywords = candidate_keywords_set.intersection(job_keywords_set)

        # 如果交集不为空，则说明匹配成功
        if matched_keywords:
            matching_jobs.append({
                'job_id': job.id,
                'title': job.title,
                'company_name': job.company.name,
                'locations': job.locations,
                'level_set': job.level_set,
                'matched_keywords': list(matched_keywords)
            })

    return matching_jobs

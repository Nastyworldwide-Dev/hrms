CLASS: a staff photo reachable without the org chart's company fence
hrms/api/profile_photo.py set_photo same-root — User.user_image now holds the fenced url, not the raw S3 key
hrms/api/org_chart.py photo same-root — signs only a url a File of that employee owns
hrms/api/org_chart.py get_node same-root — other company reads as not found; team_size scoped
hrms/patches/v16_0/repair_public_selfies.py:50 not-affected — a log line mentioning 'photo'; the patch never calls set_photo/photo/photo_url

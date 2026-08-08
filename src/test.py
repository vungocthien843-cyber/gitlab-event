import json
from fastapi import Request

payload = {
  "ref": "refs/heads/main",
  "before": "2fa1e1f6276f47a79beebb3ddca4b17df0b82bfa",
  "after": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
  "repository": {
    "id": 1327508956,
    "node_id": "R_kgDOTyAt3A",
    "name": "gitlab-event",
    "full_name": "vungocthien843-cyber/gitlab-event",
    "private": False,
    "owner": {
      "name": "vungocthien843-cyber",
      "email": "vungocthien843@gmail.com",
      "login": "vungocthien843-cyber",
      "id": 281504692,
      "node_id": "U_kgDOEMdrtA",
      "avatar_url": "https://avatars.githubusercontent.com/u/281504692?v=4",
      "gravatar_id": "",
      "url": "https://api.github.com/users/vungocthien843-cyber",
      "html_url": "https://github.com/vungocthien843-cyber",
      "followers_url": "https://api.github.com/users/vungocthien843-cyber/followers",
      "following_url": "https://api.github.com/users/vungocthien843-cyber/following{/other_user}",
      "gists_url": "https://api.github.com/users/vungocthien843-cyber/gists{/gist_id}",
      "starred_url": "https://api.github.com/users/vungocthien843-cyber/starred{/owner}{/repo}",
      "subscriptions_url": "https://api.github.com/users/vungocthien843-cyber/subscriptions",
      "organizations_url": "https://api.github.com/users/vungocthien843-cyber/orgs",
      "repos_url": "https://api.github.com/users/vungocthien843-cyber/repos",
      "events_url": "https://api.github.com/users/vungocthien843-cyber/events{/privacy}",
      "received_events_url": "https://api.github.com/users/vungocthien843-cyber/received_events",
      "type": "User",
      "user_view_type": "public",
      "site_admin": False
    },
    "html_url": "https://github.com/vungocthien843-cyber/gitlab-event",
    "description": None,
    "fork": False,
    "url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event",
    "forks_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/forks",
    "keys_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/keys{/key_id}",
    "collaborators_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/collaborators{/collaborator}",
    "teams_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/teams",
    "hooks_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/hooks",
    "issue_events_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues/events{/number}",
    "events_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/events",
    "assignees_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/assignees{/user}",
    "branches_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/branches{/branch}",
    "tags_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/tags",
    "blobs_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/blobs{/sha}",
    "git_tags_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/tags{/sha}",
    "git_refs_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/refs{/sha}",
    "trees_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/trees{/sha}",
    "statuses_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/statuses/{sha}",
    "languages_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/languages",
    "stargazers_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/stargazers",
    "contributors_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/contributors",
    "subscribers_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/subscribers",
    "subscription_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/subscription",
    "commits_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/commits{/sha}",
    "git_commits_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/git/commits{/sha}",
    "comments_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/comments{/number}",
    "issue_comment_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues/comments{/number}",
    "contents_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/contents/{+path}",
    "compare_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/compare/{base}...{head}",
    "merges_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/merges",
    "archive_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/{archive_format}{/ref}",
    "downloads_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/downloads",
    "issues_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/issues{/number}",
    "pulls_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/pulls{/number}",
    "milestones_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/milestones{/number}",
    "notifications_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/notifications{?since,all,participating}",
    "labels_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/labels{/name}",
    "releases_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/releases{/id}",
    "deployments_url": "https://api.github.com/repos/vungocthien843-cyber/gitlab-event/deployments",
    "created_at": 1786173232,
    "updated_at": "2026-08-08T09:51:36Z",
    "pushed_at": 1786182756,
    "git_url": "git://github.com/vungocthien843-cyber/gitlab-event.git",
    "ssh_url": "git@github.com:vungocthien843-cyber/gitlab-event.git",
    "clone_url": "https://github.com/vungocthien843-cyber/gitlab-event.git",
    "svn_url": "https://github.com/vungocthien843-cyber/gitlab-event",
    "homepage": "https://gitlab-event.vercel.app",
    "size": 2737,
    "stargazers_count": 0,
    "watchers_count": 0,
    "language": "Python",
    "has_issues": True,
    "has_projects": True,
    "has_downloads": True,
    "has_wiki": True,
    "has_pages": False,
    "has_discussions": False,
    "forks_count": 0,
    "mirror_url": None,
    "archived": False,
    "disabled": False,
    "open_issues_count": 0,
    "license": None,
    "allow_forking": True,
    "is_template": False,
    "web_commit_signoff_required": False,
    "has_pull_requests": True,
    "pull_request_creation_policy": "all",
    "topics": [

    ],
    "visibility": "public",
    "forks": 0,
    "open_issues": 0,
    "watchers": 0,
    "default_branch": "main",
    "stargazers": 0,
    "master_branch": "main"
  },
  "pusher": {
    "name": "vungocthien843-cyber",
    "email": "vungocthien843@gmail.com"
  },
  "forced": False,
  "sender": {
    "login": "vungocthien843-cyber",
    "id": 281504692,
    "node_id": "U_kgDOEMdrtA",
    "avatar_url": "https://avatars.githubusercontent.com/u/281504692?v=4",
    "gravatar_id": "",
    "url": "https://api.github.com/users/vungocthien843-cyber",
    "html_url": "https://github.com/vungocthien843-cyber",
    "followers_url": "https://api.github.com/users/vungocthien843-cyber/followers",
    "following_url": "https://api.github.com/users/vungocthien843-cyber/following{/other_user}",
    "gists_url": "https://api.github.com/users/vungocthien843-cyber/gists{/gist_id}",
    "starred_url": "https://api.github.com/users/vungocthien843-cyber/starred{/owner}{/repo}",
    "subscriptions_url": "https://api.github.com/users/vungocthien843-cyber/subscriptions",
    "organizations_url": "https://api.github.com/users/vungocthien843-cyber/orgs",
    "repos_url": "https://api.github.com/users/vungocthien843-cyber/repos",
    "events_url": "https://api.github.com/users/vungocthien843-cyber/events{/privacy}",
    "received_events_url": "https://api.github.com/users/vungocthien843-cyber/received_events",
    "type": "User",
    "user_view_type": "public",
    "site_admin": False
  },
  "created": False,
  "deleted": False,
  "base_ref": None,
  "compare": "https://github.com/vungocthien843-cyber/gitlab-event/compare/2fa1e1f6276f...d89caa17cd36",
  "commits": [
    {
      "id": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
      "tree_id": "b292c13656639bce513a87eb9ad0b75e6d89a6c0",
      "distinct": True,
      "message": "nthoc",
      "timestamp": "2026-08-08T16:52:31+07:00",
      "url": "https://github.com/vungocthien843-cyber/gitlab-event/commit/d89caa17cd36630afba8bfa3f7fe569a03a0005a",
      "author": {
        "name": "Vu ngon thien",
        "email": "vungocthien843@gmail.com",
        "date": "2026-08-08T16:52:31+07:00",
        "username": "vungocthien843-cyber"
      },
      "committer": {
        "name": "Vu ngon thien",
        "email": "vungocthien843@gmail.com",
        "date": "2026-08-08T16:52:31+07:00",
        "username": "vungocthien843-cyber"
      },
      "added": [

      ],
      "removed": [

      ],
      "modified": [
        "ping01.yaml"
      ]
    }
  ],
  "head_commit": {
    "id": "d89caa17cd36630afba8bfa3f7fe569a03a0005a",
    "tree_id": "b292c13656639bce513a87eb9ad0b75e6d89a6c0",
    "distinct": True,
    "message": "nthoc",
    "timestamp": "2026-08-08T16:52:31+07:00",
    "url": "https://github.com/vungocthien843-cyber/gitlab-event/commit/d89caa17cd36630afba8bfa3f7fe569a03a0005a",
    "author": {
      "name": "Vu ngon thien",
      "email": "vungocthien843@gmail.com",
      "date": "2026-08-08T16:52:31+07:00",
      "username": "vungocthien843-cyber"
    },
    "committer": {
      "name": "Vu ngon thien",
      "email": "vungocthien843@gmail.com",
      "date": "2026-08-08T16:52:31+07:00",
      "username": "vungocthien843-cyber"
    },
    "added": [

    ],
    "removed": [

    ],
    "modified": [
      "ping01.yaml"
    ]
  }
}


print(payload)

commits = payload.get("commits", [])
print("Commits:", commits)

latest_commit = commits[-1]
print("Latest Commit:", latest_commit)

changed_files = latest_commit.get("added", []) + latest_commit.get("modified", [])
print("Changed Files:", changed_files)

yaml_files = [f for f in changed_files if f.endswith('.yaml') or f.endswith('.yml')]
print("YAML Files:", yaml_files)
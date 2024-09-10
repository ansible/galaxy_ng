# Community Overview


## Context

GalaxyNG is the next generation of the codebase behind https://galaxy.ansible.com. We hope to meld this code
in a way that makes it suitable for both the customers of the Ansible Automation Platform and the community
around https://galaxy.ansible.com.


## History

### Galaxy

Galaxy launched in 2013 by the company later known as "Ansible".

> What’s Galaxy?  Ansible Galaxy is an automation content site designed from the ground up with an emphasis on being very dynamic — offering up a lot of new ways to find content.

---

> Galaxy is structured around roles.   You download the roles you like, then you write very simple play books that assemble all the roles together with roles you also write yourself.
...

> At the initial phase, we’ve made sign up as painless as we could — you can login with a local account, but you can also login with OAuth from Twitter, GitHub, or Google+.   (We just use this for login, so we won’t tweet for you or anything).   You can also link social accounts later if you sign up first with a local account, but we expect social auth is the way to go for many of you.

---

> Once you log in, from the “Explore” page, you can see not only the top roles in each category, but also the top reviewers, top authors, new roles, and new authors.  You can browse the users arbitrarily and see what they have contributed and reviewed.

---

> When we started Galaxy, a lot of our design influences were from consumer sites — things like iTunes, Flickr (Explore), and most significantly … beeradvocate.com!  For this reason you’ll see linked reviews and ratings, ratings with structure, and highlighted reviews from AnsibleWorks employees.   It’s designed to help you find what’s good very very clearly, and explore other things you might be interested in.

### Galaxy NG

GalaxyNG is a total rewrite of some features from galaxy but catered to serving collections to Red Hat customers as a SaaS on https://cloud.redhat.com (now https://console.redhat.com) and as an on-premise deployment known as "Private Automation HUB". The new codebase did not include support for standalone roles and solely focused instead on collections.

The biggest change with GalaxyNG is that it is no longer a standalone django application with an AngularJS+Bootstrap frontend. As part of the rewrite, the project became a "pulp plugin", meaning it heavily relies on the family of projects in the https://github.com/pulp organization. Galaxy's v2 api makes use of "repositories" from pulp, but it was added on top of the previous codebase rather then conforming to the pure definition of [pulp plugin](https://docs.pulpproject.org/pulpcore/plugins/index.html).


## Future

We would like to consolidate the features of https://github.com/ansible/galaxy and https://github.com/ansible/galaxy_ng
into the galaxy_ng codebase and bring community usage, contribution and improvements there. In doing so, we want to sunset
the galaxy codebase and cooperatively plan to rehost https://galaxy.ansible.com with an instance of the galaxy_ng codebase.

We do not yet have a timeline for the migration or the cut over. 


## Communication and Feedback.

The galaxy dev team, contributors and community can mostly be found on the [Ansible Forum](https://forum.ansible.com/tag/galaxy-ng).
See the [Ansible communication guide](https://docs.ansible.com/ansible/devel/community/communication.html) to learn more.

For bug reports and feature requests, see "Filing Issues".


## Filing Issues

1. Go to https://issues.redhat.com/browse/AAH (can browse without login)
2. Register for red hat account
3. Click blue “Create” button at top of screen to get a dialog box for AAH project
4. Set “Issue Type” to Bug or Task
5. Set “Summary” (give it a title) & “Description”, and mention community
6. Click “Create” at bottom of dialog box


## Creating PullRequests

See the Community Development documentation.

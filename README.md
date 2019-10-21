DMOJ Site [![Documentation Status](https://readthedocs.org/projects/dmoj/badge/?version=latest)](http://dmoj.readthedocs.org/en/latest/?badge=latest) [![Slack](https://slack.dmoj.ca/badge.svg)](https://slack.dmoj.ca)
=====
Django [AGPLv3](https://github.com/DMOJ/site/blob/master/LICENSE) contest judge frontend for the [DMOJ judge](https://github.com/DMOJ/judge) system. See it live at https://dmoj.ca/.

<table>
<tr>
<td>
<a href="http://dmoj.ca">
<img src="https://avatars2.githubusercontent.com/u/6934864?v=3&s=100" align="left"></img>
</a>
</td>
<td>
A modern online judge and contest platform system, supporting <b>IO-based</b>, <b>interactive</b>, and <b>signature-graded</b> tasks.
</td>
</tr>
</table>

## Features

### Sleek problem statements
Problems are written in Markdown, with LaTeX-enabled math and figures, as well as syntax highlighting. Problem statements can be saved to PDF for ease of distribution to contestants.


![](https://i.imgur.com/7KD7h5r.png)


### Submit in over 60 languages
Contestants may submit in over 60 programming languages with syntax highlighting. Problem authors can restrict problems to specific languages, and set language-specific resource limits. 


![](https://i.imgur.com/8CjfHQb.png)


### Live submission status
Submission pages feature live updates, and submissions may be aborted by both submission authors and administrators. Compilation errors and warnings for a number of languages feature color highlighting.


![](https://i.imgur.com/Hom0U3R.png)


Global, per-problem, and per-contest submission lists are live-updating, and can be filtered by status and language.


![](https://i.imgur.com/ouErkPY.png)


### Configurable contest system
Contests feature an optional rating system, and can be configured to run in any timeframe. Users are also able to participate virtually after the contest ends. ACM-ICPC, IOI, and AtCoder formats are supported out-of-the-box.


![](https://i.imgur.com/qcnmVeI.png)


Contests may be limited to particular organizations, or require access codes to join. Hidden scoreboards are supported. The contest system integrates with [Stanford MOSS](https://theory.stanford.edu/~aiken/moss/) to provide plagiarism checking. 
Editorial support is built-in, and editorials are automatically published once a contest ends.


### Home page blog and activity stream

Announcements from administrators, ongoing contests, recent comments and new problems are easily accessible from the home page.

![](https://i.imgur.com/zpQAoDB.png)


### Internationalized interface
Use the site in whatever language you're most comfortable in &mdash; currently fully supporting English, Simplified Chinese, and Romanian. Problem authors can provide statements in multiple languages, and DMOJ will display the most relevant one to a reader.


![](https://i.imgur.com/OeuI0o5.png)



### Highly featured administration interface
The DMOJ admin interface is highly versatile, and can be efficiently used for anything from managing users to authoring problem statements.


![](https://dmoj.ml/data/_other/readme/problem-admin.png)

![](https://dmoj.ml/data/_other/readme/admin-dashboard.png)


### Miscellaneous others
This is by no means a complete list, but other features in the DMOJ site include:

* OAuth logins with Google, Facebook, and GitHub;
* Two-factor authentication (TOTP);
* Arbitrary flatpages;
* User rating graphs;
* Registration emails;
* Automated contest email notifying;
* ...and many more!

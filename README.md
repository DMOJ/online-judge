DMOJ: Modern Online Judge [![Build Status](https://github.com/DMOJ/online-judge/workflows/build/badge.svg)](https://github.com/DMOJ/online-judge/actions/) [![Slack](https://slack.dmoj.ca/badge.svg)](https://slack.dmoj.ca)
=====

A modern [open-source](https://github.com/DMOJ/online-judge/blob/master/LICENSE) online judge and contest platform system. It has been used to host hundreds of competitions, including several national olympiads.

See it live at [dmoj.ca](https://dmoj.ca/)!

## Features

* [Support for over **60 language runtimes**](https://github.com/DMOJ/online-judge#supported-languages)
* Highly robust judging system:
   * Supports **interactive** and **signature-graded** tasks
   * Supports **runtime data generators** and **custom output validators** 
   * Specifying **per-language resource limits**
   * Capable of scaling to hundreds of judging servers
* Extremely configurable contest system:
   * Supports ICPC/IOI/AtCoder/ECOO formats out-of-the box
   * **System testing** supported
   * **Hidden scoreboards** and **virtual participation**
   * Topcoder-style **rating**
   * **Plagiarism detection** via [Stanford MOSS](https://theory.stanford.edu/~aiken/moss/)
   * Restricting contest access to particular organizations or users
* Rich problem statements, with support for **LaTeX math and diagrams**
   * Automatic **PDF generation** for easy distribution
   * Built-in support for **editorials**
* **Live updates** for submissions
* Internationalized site interface
* Home page blog and activity stream
* Fine-grained permission control for staff
* OAuth login with Google, Facebook, and Github
* Two-factor authentication support

## Installation

Check out the install documentation at [docs.dmoj.ca](https://docs.dmoj.ca/#/site/installation). Feel free to reach out to us on [Slack](https://slack.dmoj.ca) if you have any questions.

## Screenshots

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


![](https://i.imgur.com/rc7orzj.png)


### Extensible contest system
Contests feature an optional rating system, and can be configured to run in any timeframe. Users are also able to participate virtually after the contest ends. ICPC, IOI, AtCoder, and ECOO contest formats are supported out-of-the-box, and new formats can be added with custom code.


![](https://i.imgur.com/0V1fzZi.png)


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

## Supported Languages

Check out [**DMOJ/judge**](https://github.com/DMOJ/judge-server) for more judging backend details.

Supported languages include:
* C++ 11/14/17 (GCC and Clang)
* C 99/11
* Java 8/9/10/11
* Python 2/3
* PyPy 2/3
* Pascal
* Perl
* Mono C#/F#/VB

The judge can also grade in the languages listed below. These languages are less tested and more likely to be buggy.
* Ada
* AWK
* COBOL
* D
* Dart
* Fortran
* Forth
* Go
* Groovy
* GAS x86/x64/ARM
* Haskell
* INTERCAL
* Kotlin
* Lua
* NASM x86/x64
* Objective-C
* OCaml
* PHP
* Pike
* Prolog
* Racket
* Ruby
* Rust
* Scala
* Chicken Scheme
* sed
* Steel Bank Common Lisp
* Swift
* Tcl
* Turing
* V8 JavaScript
* Brain\*\*\*\*
* Zig

window.JOB_DATA = {
  "presentation_title": "Arithmetic Progression",
  "sections": [
    {
      "section_id": 1,
      "section_type": "intro",
      "title": "Introduction",
      "renderer": "none",
      "text_layer": "hide",
      "visual_layer": "hide",
      "avatar_layer": "show",
      "narration": {
        "full_text": "Welcome! Have you ever noticed the beautiful patterns in a sunflower, or how a saving plan grows steadily? These patterns aren't just in nature; they're a core concept in mathematics called progressions. In this lesson, we'll explore a specific type called Arithmetic Progression, or AP, and see how it appears in our daily lives.",
        "segments": [
          {
            "purpose": "introduce",
            "start_time": 0,
            "end_time": 17,
            "text": "Welcome! Have you ever noticed the beautiful patterns in a sunflower, or how a saving plan grows steadily? These patterns aren't just in nature; they're a core concept in mathematics called progressions."
          },
          {
            "purpose": "introduce",
            "start_time": 17,
            "end_time": 25,
            "text": "In this lesson, we'll explore a specific type called Arithmetic Progression, or AP, and see how it appears in our daily lives."
          }
        ]
      },
      "visual_beats": [
        {
          "visual_type": "text",
          "start_time": 0,
          "end_time": 25,
          "display_text": "[Teacher Welcome]"
        }
      ],
      "avatar_video": "avatars/section_1_avatar.mp4",
      "avatar_status": "completed"
    },
    {
      "section_id": 2,
      "section_type": "summary",
      "title": "Learning Objectives",
      "renderer": "none",
      "visual_type": "bullet_list",
      "text_layer": "show",
      "visual_layer": "show",
      "narration": {
        "full_text": "By the end of this lesson, you will be able to: Define an Arithmetic Progression and identify its key components. Find any term in a sequence using the nth term formula. Calculate the sum of a certain number of terms in an AP. And finally, apply these concepts to solve practical, real-world problems.",
        "segments": [
          {
            "purpose": "introduce",
            "start_time": 0,
            "end_time": 4,
            "text": "By the end of this lesson, you will be able to:"
          },
          {
            "purpose": "explain",
            "start_time": 4,
            "end_time": 9,
            "text": "Define an Arithmetic Progression and identify its key components."
          },
          {
            "purpose": "explain",
            "start_time": 9,
            "end_time": 14,
            "text": "Find any term in a sequence using the nth term formula."
          },
          {
            "purpose": "explain",
            "start_time": 14,
            "end_time": 19,
            "text": "Calculate the sum of a certain number of terms in an AP."
          },
          {
            "purpose": "explain",
            "start_time": 19,
            "end_time": 24,
            "text": "And finally, apply these concepts to solve practical, real-world problems."
          }
        ]
      },
      "visual_beats": [
        {
          "visual_type": "bullet_list",
          "start_time": 4,
          "end_time": 24,
          "items": [
            {
              "id": "bullet_1",
              "display_text": "Define an Arithmetic Progression (AP) and its components (a, d).",
              "narration_segment_ids": [
                1
              ]
            },
            {
              "id": "bullet_2",
              "display_text": "Find the nth term of an AP using the formula a_n = a + (n-1)d.",
              "narration_segment_ids": [
                2
              ]
            },
            {
              "id": "bullet_3",
              "display_text": "Calculate the sum of the first n terms of an AP.",
              "narration_segment_ids": [
                3
              ]
            },
            {
              "id": "bullet_4",
              "display_text": "Apply AP concepts to solve real-world problems.",
              "narration_segment_ids": [
                4
              ]
            }
          ]
        }
      ]
    },
    {
      "section_id": 3,
      "section_type": "content",
      "title": "Introduction to Arithmetic Progressions and Definitions",
      "renderer": "manim",
      "narration": {
        "full_text": "Namaste! You must have observed that in nature, many things follow a certain pattern. Think of the beautiful spiral of petals on a sunflower, the perfect hexagons in a honeycomb, or even the grains on a maize cob. These patterns are everywhere! Even in our daily lives, like the roll numbers in your class or the days in a week, we see these sequences. In mathematics, we have a special name for these kinds of patterns: progressions. Let's look at a simple example. Imagine Shalika puts 100 rupees into her daughter's money box, and for every birthday after, she adds 50 rupees more. The amounts in the box would be 100, 150, 200, 250, and so on. It's like saving up for Diwali, adding a fixed amount each week! In this example, we see a clear pattern: each new amount is found by adding a fixed number to the previous one. This chapter is all about understanding this simple but powerful idea. We'll also learn how to find any term in the sequence and the sum of its terms, which is super useful for solving real-life problems. Let's consider some lists of numbers. Each number in these lists is called a 'term'. So, what exactly is an Arithmetic Progression, or AP? It's a list of numbers where each term is found by adding a fixed number to the term that came before it, except for the very first term, of course. This fixed number is very important; we call it the 'common difference'. And this difference can be a positive number, a negative number, or even zero. To find this common difference, which we call 'd', we just subtract any term from the one that comes right after it. So, if we call the first term 'a', the sequence becomes 'a', then 'a plus d', then 'a plus 2d', and so on. This is the general form of an AP. Looking at this table, you can see various examples. In the first, we add 1 each time. In the second, we subtract 30. In another, we add 1. And sometimes, the common difference is zero, so every term is the same! An AP can be finite, meaning it has an end. Think of students lining up for assembly\u2014there's a last person in the queue. The list of heights has a final number, 157. Or an AP can be infinite, meaning it goes on forever without a last term, just like counting numbers. Now, let's practice. Can you find the first term and the common difference for this AP? The first term, 'a', is simply the first number, which is 3/2. To find the common difference 'd', we subtract the first term from the second. So, 1/2 minus 3/2 gives us -1. Let's check with the next pair: -1/2 minus 1/2 is also -1. Perfect! Now, let's see which of these lists form an AP. For the first one, 4, 10, 16, 22... Let's check the differences. 10 minus 4 is 6. 16 minus 10 is also 6. And 22 minus 16 is 6 again! Since the common difference is constant, this is an AP. The next two terms would be 22 plus 6, which is 28, and 28 plus 6, which is 34. What about the second list: 1, -1, -3, -5...? Let's do the math. -1 minus 1 is -2. -3 minus -1 is also -2. It seems we have a pattern! The common difference 'd' is -2. So, the next two terms are -5 plus -2, which is -7, and -7 plus -2, which is -9. Now look at the third list: -2, 2, -2, 2... The difference between the first two terms is 2 minus -2, which is 4. But the difference between the next two is -2 minus 2, which is -4. Since the difference is not the same, this is not an AP. Finally, what about 1, 1, 1, 2, 2, 2, 3, 3, 3...? The difference between the first few terms is 0. But then, the difference between 2 and 1 is 1. Since the difference changes, this list does not form an AP.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Namaste! You must have observed that in nature, many things follow a certain pattern. Think of the beautiful spiral of petals on a sunflower, the perfect hexagons in a honeycomb, or even the grains on a maize cob. These patterns are everywhere!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Even in our daily lives, like the roll numbers in your class or the days in a week, we see these sequences. In mathematics, we have a special name for these kinds of patterns: progressions.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Let's look at a simple example. Imagine Shalika puts 100 rupees into her daughter's money box, and for every birthday after, she adds 50 rupees more.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "The amounts in the box would be 100, 150, 200, 250, and so on. It's like saving up for Diwali, adding a fixed amount each week! In this example, we see a clear pattern: each new amount is found by adding a fixed number to the previous one.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "This chapter is all about understanding this simple but powerful idea. We'll also learn how to find any term in the sequence and the sum of its terms, which is super useful for solving real-life problems.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "Let's consider some lists of numbers. Each number in these lists is called a 'term'.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "So, what exactly is an Arithmetic Progression, or AP? It's a list of numbers where each term is found by adding a fixed number to the term that came before it, except for the very first term, of course.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "This fixed number is very important; we call it the 'common difference'. And this difference can be a positive number, a negative number, or even zero.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_9",
            "text": "To find this common difference, which we call 'd', we just subtract any term from the one that comes right after it. So, if we call the first term 'a', the sequence becomes 'a', then 'a plus d', then 'a plus 2d', and so on. This is the general form of an AP.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_10",
            "text": "Looking at this table, you can see various examples. In the first, we add 1 each time. In the second, we subtract 30. In another, we add 1. And sometimes, the common difference is zero, so every term is the same!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_11",
            "text": "An AP can be finite, meaning it has an end. Think of students lining up for assembly\u2014there's a last person in the queue. The list of heights has a final number, 157.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_12",
            "text": "Or an AP can be infinite, meaning it goes on forever without a last term, just like counting numbers.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_13",
            "text": "Now, let's practice. Can you find the first term and the common difference for this AP? The first term, 'a', is simply the first number, which is 3/2.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_14",
            "text": "To find the common difference 'd', we subtract the first term from the second. So, 1/2 minus 3/2 gives us -1. Let's check with the next pair: -1/2 minus 1/2 is also -1. Perfect!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_15",
            "text": "Now, let's see which of these lists form an AP. For the first one, 4, 10, 16, 22... Let's check the differences.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_16",
            "text": "10 minus 4 is 6. 16 minus 10 is also 6. And 22 minus 16 is 6 again! Since the common difference is constant, this is an AP. The next two terms would be 22 plus 6, which is 28, and 28 plus 6, which is 34.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_17",
            "text": "What about the second list: 1, -1, -3, -5...? Let's do the math.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_18",
            "text": "-1 minus 1 is -2. -3 minus -1 is also -2. It seems we have a pattern! The common difference 'd' is -2. So, the next two terms are -5 plus -2, which is -7, and -7 plus -2, which is -9.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_19",
            "text": "Now look at the third list: -2, 2, -2, 2... The difference between the first two terms is 2 minus -2, which is 4. But the difference between the next two is -2 minus 2, which is -4.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_20",
            "text": "Since the difference is not the same, this is not an AP. Finally, what about 1, 1, 1, 2, 2, 2, 3, 3, 3...? The difference between the first few terms is 0. But then, the difference between 2 and 1 is 1. Since the difference changes, this list does not form an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "You must have observed that in",
            "end_phrase": "in a pine etc.,....and"
          },
          "display_text": "You must have observed that in nature, many things follows a certain pattern such as the petals of a sunflower the holes of a honeycomb The grain in a maize cob, the spirals in a pineapple and in a pine etc.,....",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "also, if we observe in our",
            "end_phrase": "generalised in maths as progression."
          },
          "display_text": "if we observe in our regular lives, we come across, Arithmetic progression quite often, for example Roll numbers of a student's in a class, days in a week or months in a year. This pattern of series and sequence has been generalised in maths as progression.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Shalika puts \u20b9100 into her daughter",
            "end_phrase": "by \u20b9 50 every year."
          },
          "display_text": "Shalika puts \u20b9100 into her daughter money box when she was 1 year old and increased the amount by \u20b9 50 every year.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "The amount of money ( in",
            "end_phrase": "by adding a fixed numbers."
          },
          "display_text": "The amount of money ( in \u20b9 )in the box on the 1st, 2nd, 3rd, 4th, .... Birthdays were 100,150,200,250 .... respectively.\nIn the example above we observe some pattern and we found that the succeeding terms are obtained by adding a fixed numbers.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "In this chapter we shall discuss",
            "end_phrase": "solving some daily life problems."
          },
          "display_text": "In this chapter we shall discuss one of these pattern in which succeeding term are obtained by a fixed number to the preceding terms. We shall also see how to find there nth term and the sum of n consecutive and use this knowledge in solving some daily life problems.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Consider the following list of numbers",
            "end_phrase": "list is called a term"
          },
          "display_text": "Consider the following list of numbers\n* 1,2,3,5 .... * 10,20,30,40 ....\n* 20,40,60 .... * -1,0,1,2,3 ....\nEach of the numbers in the list is called a term",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "An arithmetic progression is a list",
            "end_phrase": "except the first term."
          },
          "display_text": "An arithmetic progression is a list of numbers in which each term is obtained by adding a fixed number to the preceding term except the first term.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "This fixed number is called the",
            "end_phrase": "positive, negative or zero."
          },
          "display_text": "This fixed number is called the common difference (c.d) of the arithmetic progression.\nIt can be positive, negative or zero.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_9",
          "segment_id": "seg_9",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "The common difference between the two",
            "end_phrase": "general form of an AP."
          },
          "display_text": "$$d = a_2 - a_1 = a_3 - a_2 = \\dots = a_n - a_{n-1}$$\n$a, a + d, a + 2d, a + 3d, \\dots$",
          "latex_content": "d = a_2 - a_1 = a_3 - a_2 = \\dots = a_n - a_{n-1}\na, a + d, a + 2d, a + 3d, \\dots",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_10",
          "segment_id": "seg_10",
          "visual_type": "diagram",
          "markdown_pointer": {
            "start_phrase": "| Ex 1 | 1, 2,",
            "end_phrase": "from) the term preceding it. |"
          },
          "display_text": "| Ex 1 | 1, 2, 3,<br>4,............ | Each term is 1 more than the term preceding it. |\n| Ex 2 | 100, 70, 40,<br>10,............ | Each term is 30 less than the term preceding it. |\n| Ex 3 | -3, -2, -1,<br>0,............ | Each term is obtained by adding 1 to the term preceding it. |\n| Ex 4 | 3, 3, 3,<br>3,............ | All the terms in the list are 3, i.e., each term is obtained by adding (or subtracting) 0 to the term preceding it. |\n| Ex 5 | -1, -1.5, -2.0, -<br>2.5,............ | Each term is obtained by adding -0.5 to (i.e., subtracting 0.5 from) the term preceding it. |",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_11",
          "segment_id": "seg_11",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "In an AP there are only",
            "end_phrase": "450, 500."
          },
          "display_text": "In an AP there are only a finite number of terms. Such an AP is called a finite AP. Each of these Arithmetic Progressions (APs) has a last term.\na) The heights (in cm) of some students of a school standing in a queue in the morning assembly are 147, 148, 149, ..., 157.\nb) The balance money (in Rs) after paying 5% of the total loan of Rs 1000 every month is 950, 900, 850, 800, ..., 50.\nc) The total savings (in Rs) after every month for 10 months when Rs50 are saved each month are 50, 100, 150, 200, 250, 300, 350, 400, 450, 500.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_12",
          "segment_id": "seg_12",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "In an AP there are infinite",
            "end_phrase": "-10, -15, -20 ..."
          },
          "display_text": "In an AP there are infinite number of terms. Such an AP is called a infinite AP. Each of these Arithmetic Progressions (APs) do not have last term.\na) 3, 7, 11 ...\n(b) 1, 4, 7, 10, ...\n(c) -10, -15, -20 ...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_13",
          "segment_id": "seg_13",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 1: $\\frac{3}{2}, \\frac{1}{2},",
            "end_phrase": "and the common difference 'd'."
          },
          "display_text": "Example 1: $\\frac{3}{2}, \\frac{1}{2}, -\\frac{1}{2}, -\\frac{3}{2}, \\dots$ write the first term 'a' and the common difference 'd'.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_14",
          "segment_id": "seg_14",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$\\text{Here, } a_1 = \\frac{3}{2}",
            "end_phrase": "= -\\frac{1}{2} - \\frac{1}{2} = -1$$"
          },
          "display_text": "$$\\text{Here, } a_1 = \\frac{3}{2} \\text{ d} = a_2 - a_1 = \\frac{1}{2} - \\frac{3}{2} = -1 \\quad a_3 - a_2 = -\\frac{1}{2} - \\frac{1}{2} = -1$$",
          "latex_content": "\\text{Here, } a_1 = \\frac{3}{2} \\text{ d} = a_2 - a_1 = \\frac{1}{2} - \\frac{3}{2} = -1 \\quad a_3 - a_2 = -\\frac{1}{2} - \\frac{1}{2} = -1",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_15",
          "segment_id": "seg_15",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 2: Which of the following",
            "end_phrase": "i) 4, 10, 16, 22..."
          },
          "display_text": "Example 2: Which of the following list of numbers form an AP? If they form an AP, write the next two terms\ni) 4, 10, 16, 22...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_16",
          "segment_id": "seg_16",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$a_2 - a_1 = 10 -",
            "end_phrase": "and  $28 + 6 = 34$ ."
          },
          "display_text": "$$a_2 - a_1 = 10 - 4 = 6; a_3 - a_2 = 16 - 10 = 6; a_3 - a_2 = 22 - 16 = 6$$\nSo, the given list of numbers forms an AP with the common difference  $d = 6$ .\nThe next two terms are:  $22 + 6 = 28$  and  $28 + 6 = 34$ .",
          "latex_content": "a_2 - a_1 = 10 - 4 = 6; a_3 - a_2 = 16 - 10 = 6; a_3 - a_2 = 22 - 16 = 6",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_17",
          "segment_id": "seg_17",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "ii) 1, -1, -3, -5",
            "end_phrase": "... "
          },
          "display_text": "ii) 1, -1, -3, -5 ...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_18",
          "segment_id": "seg_18",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$a_2 - a_1 = -1 -",
            "end_phrase": "and  $-7 + (-2) = -9$"
          },
          "display_text": "$$a_2 - a_1 = -1 - 1 = -2; a_3 - a_2 = -3 - (-1) = -2; a_3 - a_2 = -5 - (-3) = -2$$\nSo, the given list of numbers forms an AP with the common difference  $d = -2$ .\nThe next two terms are:  $-5 + (-2) = -7$  and  $-7 + (-2) = -9$",
          "latex_content": "a_2 - a_1 = -1 - 1 = -2; a_3 - a_2 = -3 - (-1) = -2; a_3 - a_2 = -5 - (-3) = -2",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_19",
          "segment_id": "seg_19",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "iii) -2, 2, -2, 2...",
            "end_phrase": "So, the given list of numbers does not form an AP."
          },
          "display_text": "iii) -2, 2, -2, 2...\n$$a_2 - a_1 = 2 - (-2) = 2 + 2 = 4; a_3 - a_2 = -2 - 2 = -4; a_3 - a_2 = 2 - (-2) = 2 + 2 = 4$$\nHere,  $a_{k+1} \\neq a_k$  So, the given list of numbers does not form an AP.",
          "latex_content": "a_2 - a_1 = 2 - (-2) = 2 + 2 = 4; a_3 - a_2 = -2 - 2 = -4; a_3 - a_2 = 2 - (-2) = 2 + 2 = 4",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_20",
          "segment_id": "seg_20",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "iv) 1, 1, 1, 2,",
            "end_phrase": "does not form an AP."
          },
          "display_text": "iv) 1, 1, 1, 2, 2, 2, 3, 3, 3...\n$$a_2 - a_1 = 1 - 1 = 0; a_3 - a_2 = 1 - 1 = 0; a_3 - a_2 = 2 - 1 = 1$$\n$a_2 - a_1 = a_3 - a_2 \\neq a_3 - a_2$  So, the given list of numbers does not form an AP.",
          "latex_content": "a_2 - a_1 = 1 - 1 = 0; a_3 - a_2 = 1 - 1 = 0; a_3 - a_2 = 2 - 1 = 1",
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "The scene opens with a beautiful, vibrant montage of nature's patterns: a sunflower's florets spiraling outwards, a close-up of a honeycomb with glowing hexagonal cells, and the grains on a maize cob appearing in neat rows. Transition to a colorful animation of Shalika's money box, a traditional Indian-style piggy bank. Animated coins labeled '\u20b9100' drop in, followed by '\u20b950' coins for subsequent years, with a counter on-screen showing the total: 100, 150, 200... The definition of an Arithmetic Progression appears in clean, bold text. Then, visualize the general form 'a, a+d, a+2d...' being built step-by-step. The term 'a' appears, then a glowing '+d' arrow connects it to the next term 'a+d', and so on. For Finite vs. Infinite APs, show two number lines. The finite one has clear start and end points. The infinite one extends off-screen with an animated ellipsis (...). For the final examples, each list of numbers (e.g., 4, 10, 16, 22) appears. Below them, the subtraction (10-4=6, 16-10=6) is animated, with the result '6' glowing green and a large green checkmark appearing. For non-APs, the different results (e.g., 4 and -4) glow red, and a large red 'X' animates on screen.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Patterns in Nature\", font_size=48, color=BLUE).to_edge(UP)\n        sunflower = Circle(radius=0.8, color=YELLOW, fill_opacity=0.5).shift(LEFT * 3)\n        sunflower_label = Text(\"Sunflower\", font_size=20).next_to(sunflower, DOWN)\n        honeycomb = RegularPolygon(n=6, radius=0.6, color=ORANGE, fill_opacity=0.5)\n        honeycomb_label = Text(\"Honeycomb\", font_size=20).next_to(honeycomb, DOWN)\n        maize = Rectangle(width=0.5, height=1.2, color=GOLD, fill_opacity=0.5).shift(RIGHT * 3)\n        maize_label = Text(\"Maize Cob\", font_size=20).next_to(maize, DOWN)\n        self.play(Write(title), run_time=1.0)\n        self.play(FadeIn(sunflower), FadeIn(sunflower_label), FadeIn(honeycomb), FadeIn(honeycomb_label), FadeIn(maize), FadeIn(maize_label), run_time=2.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(sunflower), FadeOut(sunflower_label), FadeOut(honeycomb), FadeOut(honeycomb_label), FadeOut(maize), FadeOut(maize_label), FadeOut(title), run_time=0.8)\n        daily_title = Text(\"Daily Life Patterns\", font_size=42, color=GREEN).to_edge(UP)\n        roll_numbers = Text(\"Roll Numbers: 1, 2, 3, 4...\", font_size=28).shift(UP)\n        days = Text(\"Days: Mon, Tue, Wed...\", font_size=28)\n        progression_def = Text(\"These are called Progressions\", font_size=32, color=YELLOW).shift(DOWN * 1.5)\n        self.play(Write(daily_title), run_time=1.0)\n        self.play(FadeIn(roll_numbers), FadeIn(days), run_time=1.5)\n        self.play(Write(progression_def), run_time=1.2)\n        self.wait(1.3)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.80s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        self.play(FadeOut(daily_title), FadeOut(roll_numbers), FadeOut(days), FadeOut(progression_def), run_time=0.7)\n        money_box = Rectangle(width=2, height=1.5, color=PURPLE, fill_opacity=0.3).shift(LEFT * 2)\n        box_label = Text(\"Money Box\", font_size=24).next_to(money_box, DOWN)\n        shalika_text = Text(\"Shalika's Savings Plan\", font_size=36, color=TEAL).to_edge(UP)\n        initial = Text(\"Start: Rs. 100\", font_size=28, color=GOLD).shift(RIGHT * 2 + UP)\n        yearly = Text(\"Each Birthday: +Rs. 50\", font_size=28, color=GOLD).shift(RIGHT * 2 + DOWN * 0.5)\n        self.play(Write(shalika_text), run_time=1.0)\n        self.play(Create(money_box), Write(box_label), run_time=1.5)\n        self.play(FadeIn(initial), FadeIn(yearly), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(initial), FadeOut(yearly), run_time=0.5)\n        amounts = Text(\"100, 150, 200, 250...\", font_size=32, color=YELLOW).shift(RIGHT * 2)\n        pattern_text = Text(\"Fixed amount added each time!\", font_size=28, color=GREEN).shift(DOWN * 2)\n        self.play(Write(amounts), run_time=2.0)\n        self.play(Write(pattern_text), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(money_box), FadeOut(box_label), FadeOut(amounts), FadeOut(pattern_text), FadeOut(shalika_text), run_time=0.8)\n        chapter_title = Text(\"Arithmetic Progressions\", font_size=48, color=BLUE).to_edge(UP)\n        goal1 = Text(\"- Find any term in sequence\", font_size=28).shift(UP * 0.5)\n        goal2 = Text(\"- Calculate sum of terms\", font_size=28).shift(DOWN * 0.5)\n        goal3 = Text(\"- Solve real-life problems\", font_size=28).shift(DOWN * 1.5)\n        self.play(Write(chapter_title), run_time=1.5)\n        self.play(FadeIn(goal1), FadeIn(goal2), FadeIn(goal3), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.80s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        self.play(FadeOut(goal1), FadeOut(goal2), FadeOut(goal3), FadeOut(chapter_title), run_time=0.7)\n        lists_title = Text(\"Lists of Numbers\", font_size=40, color=ORANGE).to_edge(UP)\n        list1 = Text(\"2, 4, 6, 8, 10\", font_size=32).shift(UP)\n        list2 = Text(\"5, 10, 15, 20\", font_size=32)\n        term_def = Text(\"Each number is a 'term'\", font_size=28, color=YELLOW).shift(DOWN * 1.5)\n        self.play(Write(lists_title), run_time=1.0)\n        self.play(FadeIn(list1), FadeIn(list2), run_time=1.5)\n        self.play(Write(term_def), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(list1), FadeOut(list2), FadeOut(term_def), FadeOut(lists_title), run_time=0.7)\n        ap_title = Text(\"Arithmetic Progression (AP)\", font_size=44, color=BLUE).to_edge(UP)\n        ap_def = Text(\"Each term = Previous term + Fixed number\", font_size=30, color=GREEN).shift(UP * 0.5)\n        ap_note = Text(\"(except the first term)\", font_size=24, color=GRAY).shift(DOWN * 0.5)\n        self.play(Write(ap_title), run_time=1.5)\n        self.play(Write(ap_def), run_time=2.0)\n        self.play(FadeIn(ap_note), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        self.play(FadeOut(ap_def), FadeOut(ap_note), run_time=0.5)\n        cd_title = Text(\"Common Difference (d)\", font_size=38, color=YELLOW).shift(UP * 1.2)\n        cd_types = Text(\"d can be: positive, negative, or zero\", font_size=28, color=WHITE).shift(DOWN * 0.3)\n        examples = Text(\"Examples: d=2, d=-3, d=0\", font_size=26, color=TEAL).shift(DOWN * 1.5)\n        self.play(Write(cd_title), run_time=1.5)\n        self.play(Write(cd_types), run_time=1.8)\n        self.play(FadeIn(examples), run_time=1.2)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 9 (40.0s - 45.0s, duration 5.0s)\n        self.play(FadeOut(cd_types), FadeOut(examples), FadeOut(cd_title), FadeOut(ap_title), run_time=0.7)\n        formula_title = Text(\"General Form of AP\", font_size=40, color=ORANGE).to_edge(UP)\n        general_form = MathTex(\"a,\", \"a+d,\", \"a+2d,\", \"a+3d,\", \"...\", font_size=40).shift(UP * 0.5)\n        first_term = Text(\"a = first term\", font_size=28, color=YELLOW).shift(DOWN * 1.0)\n        diff_term = Text(\"d = common difference\", font_size=28, color=YELLOW).shift(DOWN * 2.0)\n        self.play(Write(formula_title), run_time=1.0)\n        self.play(Write(general_form), run_time=2.0)\n        self.play(FadeIn(first_term), FadeIn(diff_term), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 10 (45.0s - 50.0s, duration 5.0s)\n        self.play(FadeOut(general_form), FadeOut(first_term), FadeOut(diff_term), FadeOut(formula_title), run_time=0.7)\n        table_title = Text(\"Examples of APs\", font_size=40, color=BLUE).to_edge(UP)\n        ex1 = Text(\"1, 2, 3, 4... (d=1)\", font_size=26).shift(UP * 1.2)\n        ex2 = Text(\"100, 70, 40... (d=-30)\", font_size=26).shift(UP * 0.3)\n        ex3 = Text(\"5, 6, 7, 8... (d=1)\", font_size=26).shift(DOWN * 0.6)\n        ex4 = Text(\"3, 3, 3, 3... (d=0)\", font_size=26).shift(DOWN * 1.5)\n        self.play(Write(table_title), run_time=1.0)\n        self.play(FadeIn(ex1), FadeIn(ex2), FadeIn(ex3), FadeIn(ex4), run_time=2.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 11 (50.0s - 55.0s, duration 5.0s)\n        self.play(FadeOut(ex1), FadeOut(ex2), FadeOut(ex3), FadeOut(ex4), FadeOut(table_title), run_time=0.7)\n        finite_title = Text(\"Finite AP\", font_size=40, color=GREEN).to_edge(UP)\n        finite_ex = Text(\"147, 150, 153, 156, 157\", font_size=32, color=WHITE).shift(UP * 0.5)\n        finite_note = Text(\"Has a last term (157)\", font_size=28, color=YELLOW).shift(DOWN * 0.8)\n        finite_analogy = Text(\"Like students in assembly line\", font_size=24, color=GRAY).shift(DOWN * 1.8)\n        self.play(Write(finite_title), run_time=1.0)\n        self.play(Write(finite_ex), run_time=1.5)\n        self.play(FadeIn(finite_note), FadeIn(finite_analogy), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 12 (55.0s - 60.0s, duration 5.0s)\n        self.play(FadeOut(finite_ex), FadeOut(finite_note), FadeOut(finite_analogy), FadeOut(finite_title), run_time=0.7)\n        infinite_title = Text(\"Infinite AP\", font_size=40, color=PURPLE).to_edge(UP)\n        infinite_ex = Text(\"1, 2, 3, 4, 5, 6...\", font_size=32, color=WHITE).shift(UP * 0.5)\n        infinite_note = Text(\"Goes on forever, no last term\", font_size=28, color=YELLOW).shift(DOWN * 0.8)\n        infinite_analogy = Text(\"Like counting numbers\", font_size=24, color=GRAY).shift(DOWN * 1.8)\n        self.play(Write(infinite_title), run_time=1.0)\n        self.play(Write(infinite_ex), run_time=1.5)\n        self.play(FadeIn(infinite_note), FadeIn(infinite_analogy), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 13 (60.0s - 65.0s, duration 5.0s)\n        self.play(FadeOut(infinite_ex), FadeOut(infinite_note), FadeOut(infinite_analogy), FadeOut(infinite_title), run_time=0.7)\n        practice_title = Text(\"Practice Problem\", font_size=40, color=ORANGE).to_edge(UP)\n        problem_ap = MathTex(r\"\\frac{3}{2},\", r\"\\frac{1}{2},\", r\"-\\frac{1}{2},\", r\"-\\frac{3}{2}...\", font_size=36).shift(UP * 0.5)\n        find_a = Text(\"First term a = ?\", font_size=30, color=YELLOW).shift(DOWN * 0.8)\n        answer_a = MathTex(r\"a = \\frac{3}{2}\", font_size=32, color=GREEN).shift(DOWN * 1.8)\n        self.play(Write(practice_title), run_time=1.0)\n        self.play(Write(problem_ap), run_time=1.5)\n        self.play(FadeIn(find_a), run_time=1.0)\n        self.play(Write(answer_a), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.70s\n        # Segment 14 (65.0s - 70.0s, duration 5.0s)\n        self.play(FadeOut(find_a), FadeOut(answer_a), run_time=0.5)\n        find_d = Text(\"Common difference d = ?\", font_size=30, color=YELLOW).shift(DOWN * 0.3)\n        calc1 = MathTex(r\"\\frac{1}{2} - \\frac{3}{2} = -1\", font_size=28, color=WHITE).shift(DOWN * 1.2)\n        calc2 = MathTex(r\"-\\frac{1}{2} - \\frac{1}{2} = -1\", font_size=28, color=WHITE).shift(DOWN * 2.0)\n        answer_d = MathTex(r\"d = -1\", font_size=32, color=GREEN).shift(DOWN * 2.8)\n        self.play(FadeIn(find_d), run_time=0.8)\n        self.play(Write(calc1), run_time=1.2)\n        self.play(Write(calc2), run_time=1.2)\n        self.play(Write(answer_d), run_time=1.0)\n        self.wait(0.8)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 15 (70.0s - 75.0s, duration 5.0s)\n        self.play(FadeOut(problem_ap), FadeOut(find_d), FadeOut(calc1), FadeOut(calc2), FadeOut(answer_d), FadeOut(practice_title), run_time=0.8)\n        check_title = Text(\"Which form an AP?\", font_size=40, color=BLUE).to_edge(UP)\n        seq1 = Text(\"4, 10, 16, 22...\", font_size=32, color=WHITE).shift(UP * 1.0)\n        check_label = Text(\"Check differences:\", font_size=28, color=YELLOW).shift(DOWN * 0.3)\n        self.play(Write(check_title), run_time=1.0)\n        self.play(Write(seq1), run_time=1.5)\n        self.play(FadeIn(check_label), run_time=1.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.80s\n        # Segment 16 (75.0s - 80.0s, duration 5.0s)\n        diff1 = MathTex(\"10 - 4 = 6\", font_size=28, color=WHITE).shift(DOWN * 1.0)\n        diff2 = MathTex(\"16 - 10 = 6\", font_size=28, color=WHITE).shift(DOWN * 1.6)\n        diff3 = MathTex(\"22 - 16 = 6\", font_size=28, color=WHITE).shift(DOWN * 2.2)\n        checkmark = Text(\"AP! d=6\", font_size=32, color=GREEN).shift(DOWN * 3.0)\n        next_terms = Text(\"Next: 28, 34\", font_size=26, color=TEAL).shift(UP * 0.3)\n        self.play(Write(diff1), run_time=0.8)\n        self.play(Write(diff2), run_time=0.8)\n        self.play(Write(diff3), run_time=0.8)\n        self.play(Write(checkmark), run_time=1.0)\n        self.play(FadeIn(next_terms), run_time=1.0)\n        self.wait(0.6)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 17 (80.0s - 85.0s, duration 5.0s)\n        self.play(FadeOut(seq1), FadeOut(check_label), FadeOut(diff1), FadeOut(diff2), FadeOut(diff3), FadeOut(checkmark), FadeOut(next_terms), run_time=0.8)\n        seq2 = Text(\"1, -1, -3, -5...\", font_size=32, color=WHITE).shift(UP * 1.0)\n        check2_label = Text(\"Check this sequence:\", font_size=28, color=YELLOW).shift(DOWN * 0.3)\n        self.play(Write(seq2), run_time=1.5)\n        self.play(FadeIn(check2_label), run_time=1.0)\n        self.wait(2.7)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 18 (85.0s - 90.0s, duration 5.0s)\n        diff2_1 = MathTex(\"-1 - 1 = -2\", font_size=28, color=WHITE).shift(DOWN * 1.0)\n        diff2_2 = MathTex(\"-3 - (-1) = -2\", font_size=28, color=WHITE).shift(DOWN * 1.6)\n        checkmark2 = Text(\"AP! d=-2\", font_size=32, color=GREEN).shift(DOWN * 2.4)\n        next_terms2 = Text(\"Next: -7, -9\", font_size=26, color=TEAL).shift(UP * 0.3)\n        self.play(Write(diff2_1), run_time=1.0)\n        self.play(Write(diff2_2), run_time=1.0)\n        self.play(Write(checkmark2), run_time=1.2)\n        self.play(FadeIn(next_terms2), run_time=1.0)\n        self.wait(0.8)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 19 (90.0s - 95.0s, duration 5.0s)\n        self.play(FadeOut(seq2), FadeOut(check2_label), FadeOut(diff2_1), FadeOut(diff2_2), FadeOut(checkmark2), FadeOut(next_terms2), run_time=0.8)\n        seq3 = Text(\"-2, 2, -2, 2...\", font_size=32, color=WHITE).shift(UP * 1.0)\n        diff3_1 = MathTex(\"2 - (-2) = 4\", font_size=28, color=WHITE).shift(DOWN * 0.5)\n        diff3_2 = MathTex(\"-2 - 2 = -4\", font_size=28, color=WHITE).shift(DOWN * 1.3)\n        self.play(Write(seq3), run_time=1.2)\n        self.play(Write(diff3_1), run_time=1.2)\n        self.play(Write(diff3_2), run_time=1.2)\n        self.wait(1.4)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.80s\n        # Segment 20 (95.0s - 100.0s, duration 5.0s)\n        cross3 = Text(\"NOT an AP!\", font_size=32, color=RED).shift(DOWN * 2.2)\n        self.play(Write(cross3), run_time=1.0)\n        self.wait(0.5)\n        self.play(FadeOut(seq3), FadeOut(diff3_1), FadeOut(diff3_2), FadeOut(cross3), run_time=0.5)\n        seq4 = Text(\"1, 1, 1, 2, 2, 2, 3...\", font_size=30, color=WHITE).shift(UP * 0.8)\n        note4 = Text(\"Difference changes (0, then 1)\", font_size=26, color=WHITE).shift(DOWN * 0.5)\n        cross4 = Text(\"NOT an AP!\", font_size=32, color=RED).shift(DOWN * 1.5)\n        self.play(Write(seq4), run_time=1.0)\n        self.play(FadeIn(note4), run_time=1.0)\n        self.play(Write(cross4), run_time=1.0)\n        self.wait(1.0)\n        # Hard Sync WARNING: Animation exceeds audio by 6.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      },
      "content": "# Arithmetic progression\n\n## Introduction:\n\nYou must have observed that in nature, many things follows a certain pattern such as the petals of a sunflower the holes of a honeycomb The grain in a maize cob, the spirals in a pineapple and in a pine etc.,....and also, if we observe in our regular lives, we come across, Arithmetic progression quite often, for example Roll numbers of a student's in a class, days in a week or months in a year. This pattern of series and sequence has been generalised in maths as progression.\n\n### Example :\n\nShalika puts \u20b9100 into her daughter money box when she was 1 year old and increased the amount by \u20b9 50 every year. The amount of money ( in \u20b9 )in the box on the 1<sup>st</sup>, 2<sup>nd</sup>, 3<sup>rd</sup>, 4<sup>th</sup>, .... Birthdays were 100,150,200,250 .... respectively.\n\nIn the example above we observe some pattern and we found that the succeeding terms are obtained by adding a fixed numbers.\n\nIn this chapter we shall discuss one of these pattern in which succeeding term are obtained by a fixed number to the preceding terms.\n\nWe shall also see how to find there  $n^{th}$  term and the sum of  $n$  consecutive and use this knowledge in solving some daily life problems.\n\n## 1.2 Arithmetic progression:\n\nConsider the following list of numbers\n\n\\* 1,2,3,5 .... \\* 10,20,30,40 ....\n\n\\* 20,40,60 .... \\* -1,0,1,2,3 ....\n\nEach of the numbers in the list is called a term\n\n### Definition :\n\nAn arithmetic progression is a list of numbers in which each term is obtained by adding a fixed number to the preceding term except the first term.\n\nThis fixed number is called the common difference (c.d) of the arithmetic progression.\n\nIt can be positive, negative or zero.\n\n## Common difference in the A.P\n\nIn this progression for a given series the terms used are the first term  $a_1$  second terms  $a_2$  ...  $n^{th}$  terms are  $a_n$  and the common difference by  $d$ . Then the AP becomes  $a_1$ ,  $a_2, a_3 \\dots a_n$\n\nThe common difference between the two terms and the  $n^{th}$  terms is\n\n$$d = a_2 - a_1 = a_3 - a_2 = \\dots = a_n - a_{n-1}$$\n\nwhere  $d$  is common difference, it can be +ve, -ve and zero\n\n$a, a + d, a + 2d, a + 3d, \\dots$\n\nRepresents an arithmetic progression where  $a$  is the first term and  $d$  the common difference. This is called the general form of an AP.\n\n| Ex 1 | 1, 2, 3,<br>4,............            | Each term is 1 more than the term preceding it.                                                                     |\n|------|---------------------------------------|---------------------------------------------------------------------------------------------------------------------|\n| Ex 2 | 100, 70, 40,<br>10,............       | Each term is 30 less than the term preceding it.                                                                    |\n| Ex 3 | -3, -2, -1,<br>0,............         | Each term is obtained by adding 1 to the term preceding it.                                                         |\n| Ex 4 | 3, 3, 3,<br>3,............            | All the terms in the list are 3, i.e., each term is obtained by adding (or subtracting) 0 to the term preceding it. |\n| Ex 5 | -1, -1.5, -2.0, -<br>2.5,............ | Each term is obtained by adding -0.5 to (i.e., subtracting 0.5 from) the term preceding it.                         |\n\n### Finite AP.:\n\nIn an AP there are only a finite number of terms. Such an AP is called a finite AP. Each of these Arithmetic Progressions (APs) has a last term.\n\na) The heights (in cm) of some students of a school standing in a queue in the morning assembly are 147, 148, 149, ..., 157.\n\nb) The balance money (in Rs) after paying 5% of the total loan of Rs 1000 every month is 950, 900, 850, 800, ..., 50.\n\nc) The total savings (in Rs) after every month for 10 months when Rs50 are saved each month are 50, 100, 150, 200, 250, 300, 350, 400, 450, 500.\n\n### Infinite AP.:\n\nIn an AP there are infinite number of terms. Such an AP is called a infinite AP. Each of these Arithmetic Progressions (APs) do not have last term.\n\na) 3, 7, 11 ...  \n(b) 1, 4, 7, 10, ...  \n(c) -10, -15, -20 ...\n\nNote: You will If we know the first term  $a'$  and the common difference  $d'$  then we can write an AP.\n\nExample 1:  $\\frac{3}{2}, \\frac{1}{2}, -\\frac{1}{2}, -\\frac{3}{2}, \\dots$  write the first term 'a' and the common difference 'd'.\n\n$$\\text{Here, } a_1 = \\frac{3}{2} \\text{ d} = a_2 - a_1 = \\frac{1}{2} - \\frac{3}{2} = -1 \\quad a_3 - a_2 = -\\frac{1}{2} - \\frac{1}{2} = -1$$\n\nExample 2: Which of the following list of numbers form an AP? If they form an AP, write the next two terms\n\ni) 4, 10, 16, 22...  \n(ii) 1, -1, -3, -5 ...  \n(iii) -2, 2, -2, 2...  \n(iv) 1, 1, 1, 2, 2, 2, 3, 3, 3...\n\n**Solution:**\n\ni) 4, 10, 16, 22 ...\n\n$$a_2 - a_1 = 10 - 4 = 6; a_3 - a_2 = 16 - 10 = 6; a_3 - a_2 = 22 - 16 = 6$$\n\nSo, the given list of numbers forms an AP with the common difference  $d = 6$ .\n\nThe next two terms are:  $22 + 6 = 28$  and  $28 + 6 = 34$ .\n\nii) 1, -1, -3, -5 ...\n\n$$a_2 - a_1 = -1 - 1 = -2; a_3 - a_2 = -3 - (-1) = -2; a_3 - a_2 = -5 - (-3) = -2$$\n\nSo, the given list of numbers forms an AP with the common difference  $d = -2$ .\n\nThe next two terms are:  $-5 + (-2) = -7$  and  $-7 + (-2) = -9$\n\niii) -2, 2, -2, 2...\n\n$$a_2 - a_1 = 2 - (-2) = 2 + 2 = 4; a_3 - a_2 = -2 - 2 = -4; a_3 - a_2 = 2 - (-2) = 2 + 2 = 4$$\n\nHere,  $a_{k+1} \\neq a_k$  So, the given list of numbers does not form an AP.\n\niv) 1, 1, 1, 2, 2, 2, 3, 3, 3...\n\n$$a_2 - a_1 = 1 - 1 = 0; a_3 - a_2 = 1 - 1 = 0; a_3 - a_2 = 2 - 1 = 1$$\n\n$a_2 - a_1 = a_3 - a_2 \\neq a_3 - a_2$  So, the given list of numbers does not form an AP.\n\n"
    },
    {
      "section_id": 4,
      "section_type": "content",
      "title": "Exercise 5.1: Identifying APs in Daily Life",
      "renderer": "manim",
      "narration": {
        "full_text": "Chalo! Let's put our knowledge to the test with some real-world examples from Exercise 5.1. We need to figure out if these situations create an Arithmetic Progression. First up, consider a taxi fare. Imagine you're booking an auto in Bangalore. The first kilometer is a fixed price of Rs 15, and then every extra kilometer adds a fixed Rs 8. Is this an AP? Now watch this. The fare starts at 15. For the next km, we add 8, getting 23. For the one after, we add another 8, getting 31. See how the increase is constant at 8 rupees? That's our common difference, 'd'. So yes, this is an AP. Next, a different situation. A vacuum pump removes one-fourth of the *remaining* air each time. Think about it, is the amount of air being removed constant? Let's see. The initial volume is V. The first pump leaves 3/4 V. The second pump removes 1/4 of *that*, leaving 9/16 V. The calculation shows the difference is not constant. The amount removed changes each time, so this is not an AP. Now, how about digging a well? It costs Rs 150 for the first metre and rises by a fixed Rs 50 for every subsequent metre. This should be familiar. The costs are 150, then 200, then 250. The difference is always 50. Since we are adding a fixed amount each time, this is a perfect example of an AP. Finally, what about money growing with compound interest? Like a 'fixed deposit' that gets interest calculated on the new total every year. Let's say Rs 10,000 at 8% per annum. The first year, you earn Rs 800 interest, making the total 10,800. But the next year, you earn interest on that new, larger amount, which is Rs 864. The amount of interest added is not the same. So, compound interest does not form an AP.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Chalo! Let's put our knowledge to the test with some real-world examples from Exercise 5.1. We need to figure out if these situations create an Arithmetic Progression. First up, consider a taxi fare. Imagine you're booking an auto in Bangalore. The first kilometer is a fixed price of Rs 15, and then every extra kilometer adds a fixed Rs 8. Is this an AP?",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Now watch this. The fare starts at 15. For the next km, we add 8, getting 23. For the one after, we add another 8, getting 31. See how the increase is constant at 8 rupees? That's our common difference, 'd'. So yes, this is an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Next, a different situation. A vacuum pump removes one-fourth of the *remaining* air each time. Think about it, is the amount of air being removed constant?",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Let's see. The initial volume is V. The first pump leaves 3/4 V. The second pump removes 1/4 of *that*, leaving 9/16 V. The calculation shows the difference is not constant. The amount removed changes each time, so this is not an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "Now, how about digging a well? It costs Rs 150 for the first metre and rises by a fixed Rs 50 for every subsequent metre. This should be familiar.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "The costs are 150, then 200, then 250. The difference is always 50. Since we are adding a fixed amount each time, this is a perfect example of an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "Finally, what about money growing with compound interest? Like a 'fixed deposit' that gets interest calculated on the new total every year. Let's say Rs 10,000 at 8% per annum.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "The first year, you earn Rs 800 interest, making the total 10,800. But the next year, you earn interest on that new, larger amount, which is Rs 864. The amount of interest added is not the same. So, compound interest does not form an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "1. The taxi fare after each",
            "end_phrase": "for each additional **km**"
          },
          "display_text": "The taxi fare after each **km** when the fare is **Rs15** for the first **km** and **Rs8** for each additional **km**",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Solution: The first term  $a_1 = 15$ ,",
            "end_phrase": "except first term."
          },
          "display_text": "Solution: The first term  $a_1 = 15$ ,  $a_2 = 15 + 8 = 23$ ,  $a_3 = 23 + 8 = 31$  ...\n\nHere, each term is obtained by adding a common difference = 8, except first term.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "1. The amount of air present",
            "end_phrase": "the cylinder at a time."
          },
          "display_text": "The amount of air present in a cylinder when a vacuum removes  $\\frac{1}{4}$  of the air remaining in the cylinder at a time.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_2 - a_1 = \\frac{3V}{4} - V",
            "end_phrase": "does not form an AP$$"
          },
          "display_text": "$$a_2 - a_1 = \\frac{3V}{4} - V = -\\frac{V}{4}; a_3 - a_2 = \\frac{9V}{16} - \\frac{3V}{4} = \\frac{9V}{16} - \\frac{12V}{16} = -\\frac{3V}{16}$$\n$$\\therefore a_2 - a_1 \\neq a_3 - a_2, \\therefore \\text{Hence, it does not form an AP}$$",
          "latex_content": "$$a_2 - a_1 = \\frac{3V}{4} - V = -\\frac{V}{4}; a_3 - a_2 = \\frac{9V}{16} - \\frac{3V}{4} = \\frac{9V}{16} - \\frac{12V}{16} = -\\frac{3V}{16}$$\n$$\\therefore a_2 - a_1 \\neq a_3 - a_2, \\therefore \\text{Hence, it does not form an AP}$$",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "iii). The cost digging a well",
            "end_phrase": "for each subsequent metre."
          },
          "display_text": "The cost digging a well after every metre of digging, when it costs **Rs150** for the first metre and rises by **Rs50** for each subsequent metre.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Thus the list of numbers is 150,",
            "end_phrase": "50; So it forms an AP."
          },
          "display_text": "Thus the list of numbers is 150, 200, 250, 300, .......\n\nHere, we can find the common difference = 50; So it forms an AP.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "iv). The amount of money in",
            "end_phrase": "at **8%** per annum."
          },
          "display_text": "The amount of money in the account every year, when Rs 10000 is deposited at compound interest at **8%** per annum.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_2 - a_1 = 10800 - 10000 = 800;",
            "end_phrase": "does not form an AP."
          },
          "display_text": "$$a_2 - a_1 = 10800 - 10000 = 800; a_3 - a_2 = 11664 - 10800 = 864$$\n\nThere for  $a_2 - a_1 \\neq a_3 - a_2$ ; Hence it does not form an AP.",
          "latex_content": "$$a_2 - a_1 = 10800 - 10000 = 800; a_3 - a_2 = 11664 - 10800 = 864$$\n\nThere for  $a_2 - a_1 \\neq a_3 - a_2$ ; Hence it does not form an AP.",
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "Scene opens with title 'Exercise 5.1: Real-World APs'. Animation 1: An auto-rickshaw icon moves along a number line from 0 to 15. A '+8' label appears, and it jumps to 23. Another '+8' appears, and it jumps to 31. Text 'd = 8 (Constant)' fades in with a green checkmark. Animation 2: A cylinder graphic appears with 'V' inside. It shrinks, and the label changes to '3V/4'. It shrinks again, label becomes '9V/16'. Side-by-side calculations `a2-a1 = -V/4` and `a3-a2 = -3V/16` appear. A 'Not Equal' sign flashes between them, followed by a red 'X'. Animation 3: A shovel icon digs down. A vertical line is marked '1m: \u20b9150', then '2m: \u20b9200', '3m: \u20b9250'. A '+50' label animates between each cost. A green checkmark appears. Animation 4: A bank icon with '\u20b910000'. The amount updates to '\u20b910800' as '+800' flies in. Then it updates to '\u20b911664' as '+864' flies in. The numbers 800 and 864 are highlighted and a 'Not Equal' sign flashes, followed by a red 'X'. The color palette is vibrant, using saffron, white, and green.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1\n        title = Text(\"Exercise 5.1: Real-World APs\", font_size=40).to_edge(UP)\n        self.play(Write(title), run_time=1.5)\n        \n        auto_icon = Rectangle(width=1.5, height=0.8, color=YELLOW, fill_opacity=0.7)\n        auto_icon.shift(LEFT * 5 + DOWN * 0.5)\n        \n        number_line = NumberLine(x_range=[0, 35, 5], length=10, include_numbers=False)\n        number_line.shift(DOWN * 0.5)\n        \n        label_0 = Text(\"0\", font_size=24).next_to(number_line.n2p(0), DOWN)\n        label_15 = Text(\"Rs.15\", font_size=24).next_to(number_line.n2p(15), DOWN)\n        \n        self.play(Create(number_line), Write(label_0), run_time=1.0)\n        self.play(FadeIn(auto_icon), Write(label_15), run_time=1.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2\n        plus_8_1 = Text(\"+8\", font_size=28, color=GREEN).next_to(number_line.n2p(19), UP)\n        label_23 = Text(\"Rs.23\", font_size=24).next_to(number_line.n2p(23), DOWN)\n        \n        self.play(auto_icon.animate.move_to(number_line.n2p(23) + DOWN * 0.5), \n                  Write(plus_8_1), Write(label_23), run_time=1.5)\n        \n        plus_8_2 = Text(\"+8\", font_size=28, color=GREEN).next_to(number_line.n2p(27), UP)\n        label_31 = Text(\"Rs.31\", font_size=24).next_to(number_line.n2p(31), DOWN)\n        \n        self.play(auto_icon.animate.move_to(number_line.n2p(31) + DOWN * 0.5),\n                  Write(plus_8_2), Write(label_31), run_time=1.5)\n        \n        d_text = Text(\"d = 8 (Constant)\", font_size=32, color=GREEN).to_edge(DOWN)\n        checkmark = Text(\"OK\", font_size=48, color=GREEN).next_to(d_text, RIGHT)\n        \n        self.play(Write(d_text), Write(checkmark), run_time=1.0)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3\n        self.play(FadeOut(auto_icon, number_line, label_0, label_15, label_23, label_31, \n                          plus_8_1, plus_8_2, d_text, checkmark), run_time=0.5)\n        \n        cylinder = Circle(radius=1.2, color=BLUE, fill_opacity=0.3)\n        cylinder.shift(LEFT * 3)\n        v_label = MathTex(\"V\", font_size=48).move_to(cylinder.get_center())\n        \n        question = Text(\"Air removed: 1/4 each time?\", font_size=32).to_edge(UP).shift(DOWN * 0.8)\n        \n        self.play(Create(cylinder), Write(v_label), Write(question), run_time=2.0)\n        self.wait(3.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 4\n        self.play(cylinder.animate.scale(0.75), run_time=0.8)\n        v_label_2 = MathTex(\"3V/4\", font_size=40).move_to(cylinder.get_center())\n        self.play(Transform(v_label, v_label_2), run_time=0.5)\n        \n        self.play(cylinder.animate.scale(0.75), run_time=0.8)\n        v_label_3 = MathTex(\"9V/16\", font_size=36).move_to(cylinder.get_center())\n        self.play(Transform(v_label, v_label_3), run_time=0.5)\n        \n        calc1 = MathTex(\"a_2 - a_1 = -V/4\", font_size=28).shift(RIGHT * 2.5 + UP * 0.5)\n        calc2 = MathTex(\"a_3 - a_2 = -3V/16\", font_size=28).shift(RIGHT * 2.5 + DOWN * 0.5)\n        not_equal = Text(\"Not Equal\", font_size=32, color=RED).shift(RIGHT * 2.5 + DOWN * 1.8)\n        x_mark = Text(\"X\", font_size=48, color=RED).next_to(not_equal, DOWN)\n        \n        self.play(Write(calc1), Write(calc2), run_time=1.0)\n        self.play(Write(not_equal), Write(x_mark), run_time=0.8)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 4.90s\n        # Segment 5\n        self.play(FadeOut(cylinder, v_label, question, calc1, calc2, not_equal, x_mark), run_time=0.5)\n        \n        shovel = Triangle(color=\"#8B4513\", fill_opacity=0.7).scale(0.6).shift(LEFT * 4 + UP * 1)\n        well_line = Line(LEFT * 3 + UP * 1, LEFT * 3 + DOWN * 2, color=WHITE, stroke_width=4)\n        \n        well_title = Text(\"Digging a Well\", font_size=36).to_edge(UP).shift(DOWN * 0.8)\n        \n        self.play(Write(well_title), Create(well_line), FadeIn(shovel), run_time=2.0)\n        self.wait(3.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 6\n        mark_1m = Text(\"1m: Rs.150\", font_size=28).next_to(well_line.point_from_proportion(0.33), RIGHT)\n        mark_2m = Text(\"2m: Rs.200\", font_size=28).next_to(well_line.point_from_proportion(0.66), RIGHT)\n        mark_3m = Text(\"3m: Rs.250\", font_size=28).next_to(well_line.point_from_proportion(1.0), RIGHT)\n        \n        self.play(Write(mark_1m), run_time=0.8)\n        \n        plus_50_1 = Text(\"+50\", font_size=28, color=GREEN).next_to(mark_1m, DOWN, buff=0.2)\n        self.play(Write(mark_2m), Write(plus_50_1), run_time=0.8)\n        \n        plus_50_2 = Text(\"+50\", font_size=28, color=GREEN).next_to(mark_2m, DOWN, buff=0.2)\n        self.play(Write(mark_3m), Write(plus_50_2), run_time=0.8)\n        \n        ap_check = Text(\"AP: d = 50\", font_size=32, color=GREEN).to_edge(DOWN)\n        checkmark2 = Text(\"OK\", font_size=48, color=GREEN).next_to(ap_check, RIGHT)\n        \n        self.play(Write(ap_check), Write(checkmark2), run_time=1.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 4.90s\n        # Segment 7\n        self.play(FadeOut(shovel, well_line, well_title, mark_1m, mark_2m, mark_3m, \n                          plus_50_1, plus_50_2, ap_check, checkmark2), run_time=0.5)\n        \n        bank_icon = Rectangle(width=2, height=1.5, color=GOLD, fill_opacity=0.5)\n        bank_icon.shift(LEFT * 3)\n        bank_text = Text(\"BANK\", font_size=24, color=BLACK).move_to(bank_icon.get_center())\n        \n        amount = Text(\"Rs.10,000\", font_size=32).next_to(bank_icon, RIGHT, buff=0.5)\n        interest_text = Text(\"8% per annum\", font_size=28).to_edge(UP).shift(DOWN * 0.8)\n        \n        self.play(Create(bank_icon), Write(bank_text), Write(amount), Write(interest_text), run_time=2.5)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 8\n        interest_1 = Text(\"+800\", font_size=28, color=YELLOW).next_to(amount, UP)\n        amount_2 = Text(\"Rs.10,800\", font_size=32).next_to(bank_icon, RIGHT, buff=0.5)\n        \n        self.play(Write(interest_1), run_time=0.8)\n        self.play(Transform(amount, amount_2), run_time=0.8)\n        \n        interest_2 = Text(\"+864\", font_size=28, color=YELLOW).next_to(amount, UP)\n        amount_3 = Text(\"Rs.11,664\", font_size=32).next_to(bank_icon, RIGHT, buff=0.5)\n        \n        self.play(Transform(interest_1, interest_2), run_time=0.8)\n        self.play(Transform(amount, amount_3), run_time=0.8)\n        \n        comparison = Text(\"800 vs 864: Not Equal\", font_size=28, color=RED).to_edge(DOWN)\n        x_mark2 = Text(\"X\", font_size=48, color=RED).next_to(comparison, RIGHT)\n        \n        self.play(Write(comparison), Write(x_mark2), run_time=1.0)\n        self.wait(0.6)\n        # Hard Sync WARNING: Animation exceeds audio by 4.80s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      },
      "content": "## EXERCISE 5.1\n\n1. In which of the following situations, does the list of numbers involved make an arithmetic progression, and why?\n   1. The taxi fare after each **km** when the fare is **Rs15** for the first **km** and **Rs8** for each additional **km**\n\nSolution: The first term  $a_1 = 15$ ,  $a_2 = 15 + 8 = 23$ ,  $a_3 = 23 + 8 = 31$  ...\n\nHere, each term is obtained by adding a common difference = 8, except first term.\n\n1. The amount of air present in a cylinder when a vacuum removes  $\\frac{1}{4}$  of the air remaining in the cylinder at a time.\n\nSolution: Let the initial volume of the air present in the cylinder be  $V$ .\n\nThe remaining air in the cylinder after using vacuum pump first time  $V - \\frac{1}{4} = \\frac{3V}{4}$ .\n\nRemaining air in the cylinder after using vacuum pump second time\n\n$$\\frac{3V}{4} - \\frac{3V}{4} \\times \\frac{1}{4} = \\frac{3V}{4} - \\frac{3V}{16} = \\frac{9V}{16} \\text{ and so on.}; \\text{ Here, the terms are } V, \\frac{3V}{4}, \\frac{9V}{16}, \\dots$$\n$$a_2 - a_1 = \\frac{3V}{4} - V = -\\frac{V}{4}; a_3 - a_2 = \\frac{9V}{16} - \\frac{3V}{4} = \\frac{9V}{16} - \\frac{12V}{16} = -\\frac{3V}{16}$$\n$$\\therefore a_2 - a_1 \\neq a_3 - a_2, \\therefore \\text{Hence, it does not form an AP}$$\n\niii). The cost digging a well after every metre of digging, when it costs **Rs150** for the first metre and rises by **Rs50** for each subsequent metre.\n\nSolution: The cost of digging for the first meter = Rs 150\n\nCost of digging for the second meter = 150 + 50 = Rs 200\n\nCost of digging for the third meter = 200 + 50 = Rs 250\n\nCost of digging for the fourth meter = 250 + 50 = Rs 300\n\nThus the list of numbers is 150, 200, 250, 300, .......\n\nHere, we can find the common difference = 50; So it forms an AP.\n\niv). The amount of money in the account every year, when Rs 10000 is deposited at compound interest at **8%** per annum.\n\nSolution: We know that amount  $A = P\\left(1 + \\frac{r}{100}\\right)^n$ ; Here, P = 10,000; r = 8%, n = 1, 2, 3 ...\n\n$$\\text{Amount in first year} = 10000 \\left(1 + \\frac{8}{100}\\right)^1 = 10000 \\times \\frac{108}{100} = 100 \\times 108 = \\text{Rs } 10800$$\n\n$$\\text{Amount in second year} = 10000 \\left(1 + \\frac{8}{100}\\right)^2 = 10000 \\times \\frac{108}{100} \\times \\frac{108}{100} = 108 \\times 108 = \\text{Rs } 11664$$\n\nThus the list of numbers is 10000, 10800, 11664 ...\n\n$$a_2 - a_1 = 10800 - 10000 = 800; a_3 - a_2 = 11664 - 10800 = 864$$\n\nThere for  $a_2 - a_1 \\neq a_3 - a_2$ ; Hence it does not form an AP.\n\n2. Write first four terms of the AP, when the first term 'a' and the common difference 'd' are given as follows:\n\ni)\n\n$$\\text{(i) } a = 10, d = 10$$\n\n$$\\text{(ii) } a = -2, d = 0$$\n\n$$\\text{(iii) } a = -2, d = 0$$\n\n$$\\text{(iv) } a = -1, d = \\frac{1}{2} \\text{ (v) } a = 10, d = 10$$\n\n$$\\text{(i) } a = 10, d = 10$$\n\n$$a_1 = 10;$$\n\n$$a_2 = a_1 + d = 10 + 10 = 20$$\n\n$$a_3 = a_2 + d = 20 + 10 = 30;$$\n\n$$a_4 = a_3 + d = 30 + 10 = 40$$\n\nThus the first four terms of an AP are 10, 20, 30, 40\n\n$$\\text{(ii) } a = -2, d = 0$$\n\n$$a_1 = -2;$$\n\n$$a_2 = a_1 + d = -2 + 0 = -2$$\n\n$$a_3 = a_2 + d = -2 + 0 = -2;$$\n\n$$a_4 = a_3 + d = -2 + 0 = -2$$\n\nThus the first four terms of an AP are -2, -2, -2, -2,\n\n$$\\text{(iii) } a = 4, d = -3$$\n\n$$a_1 = 4;$$\n\n$$a_2 = a_1 + d = 4 - 3 = 1$$\n\n$$a_3 = a_2 + d = 1 - 3 = -2;$$\n\n$$a_4 = a_3 + d = -2 - 3 = -5$$\n\nThus the first four terms of an AP are 4, 1, -2, -5\n\n$$(iv) a = -1, d = \\frac{1}{2}$$\n\n$$a_1 = -1;$$\n\n$$a_2 = a_1 + d = -1 + \\frac{1}{2} = -\\frac{1}{2}$$\n\n$$a_3 = a_2 + d = -\\frac{1}{2} + \\frac{1}{2} = 0; a_4 = \\frac{1}{2}$$\n\nThus the first four terms of an AP are  $-1, -\\frac{1}{2}, 0, \\frac{1}{2}$\n\n$$(v) a = -1.25, d = -0.25$$\n\n$$a_1 = -1.25; a_2 = a_1 + d = -1.25 - 0.25 = -1.50$$\n\n$$a_3 = a_2 + d = -1.50 - 0.25 = -1.75; a_4 = a_3 + d = -1.75 + 0.25 = -2.00$$\n\nThus the first four terms of an AP are  $-1.25, -1.50, -1.75, -2.00$\n\n3. For the following APs, write the first term and the common difference:\n\ni) 3, 1, -1, -3...\n\nii) -5, -1, 3, 7...\n\niii)  $\\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\dots$\n\niv) 0.6, 1.7, 2.8, 3.9, ...\n\nSolution:\n\ni) 3, 1, -1, -3...\n\nThe first term  $a = 3$ ,\n\nCommon difference\n\n$$d = a_2 - a_1 = 1 - 3 = -2$$\n\nii) -5, -1, 3, 7, ...\n\nThe first term  $a = 5$ ,\n\nCommon difference\n\n$$d = a_2 - a_1 = -1 - (-5) = -1 + 5 = 4$$\n\niii)  $\\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\dots$\n\nThe first term  $a = \\frac{1}{2}$ ,\n\nCommon difference\n\n$$d = a_2 - a_1 = \\frac{1}{2} - \\frac{1}{2} = 0$$\n\niv) 0.6, 1.7, 2.8, 3.9, ...\n\nThe first term  $a = 0.6$ ,\n\nCommon difference\n\n$$d = a_2 - a_1 = 1.7 - 0.6 = 1.1$$\n\n4. Which of the following are APs? If they form an AP, find the common difference 'd' and write three more terms\n\ni) 2, 4, 8, 16...\n\n(ii)  $2, \\frac{5}{2}, 3, \\frac{7}{2}, \\dots$\n\n(iii) -1.2, -3.2, -5.2, -7.2\n\n(iv) -10, -6, -2, 2...\n\n(v)  $3, 3 + \\sqrt{2}, 3 + 2\\sqrt{2}, 3 + 3\\sqrt{2}, \\dots$  (vi) 0.2, 0.22, 0.222, 0.2222...\n\n(vii) 0, -4, -8, -12... (viii)  $-\\frac{1}{2}, -\\frac{1}{2}, -\\frac{1}{2}, -\\frac{1}{2}, \\dots$  (ix) 1, 3, 9, 27... (x) a, 2a, 3a, 4a... (xi) a,  $a^2, a^3, a^4, \\dots$\n\n(xii)  $\\sqrt{2}, \\sqrt{8}, \\sqrt{18}, \\sqrt{32} \\dots$  (xiii)  $\\sqrt{3}, \\sqrt{6}, \\sqrt{9}, \\sqrt{12} \\dots$\n\n(xiv)  $1^1, 3^2, 5^2, 7^2 \\dots$  (xv)  $1^1, 5^2, 7^2, 73 \\dots$\n\n(i) 2, 4, 8, 16 ...\n\n$$a_2 - a_1 = 4 - 2 = 2$$\n\n$$a_3 - a_2 = 8 - 4 = 4$$\n\nHere,  $a_2 - a_1 \\neq a_3 - a_2$\n\n$\\therefore$  The given list of numbers does not form an AP.\n\nii)  $2, \\frac{5}{2}, 3, \\frac{7}{2} \\dots$\n\n$$a_2 - a_1 = \\frac{5}{2} - 2 = \\frac{1}{2}; a_3 - a_2 = 3 - \\frac{5}{2} = \\frac{1}{2}$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  Therefore the given list of numbers forms an AP with common difference\n\n$$\\frac{7}{2} + \\frac{1}{2} = 4; 4 + \\frac{1}{2} = \\frac{9}{2}; \\frac{9}{2} + \\frac{1}{2} = 5$$\n\niii)  $-1.2, -3.2, -5.2, -7.2 \\dots$\n\n$$a_2 - a_1 = -3.2 - (-1.2) = -3.2 + 1.2 = -2$$\n\n$$a_3 - a_2 = -5.2 - (-3.2) = -5.2 + 3.2 = -2$$\n\n$$a_4 - a_3 = -7.2 - (-5.2) = -7.2 + 5.2 = -2$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  The given list of numbers forms an AP with common difference  $d = -2$\n\nNext 3 terms are,  $-9.2, -11.2, -13.2$\n\niv)  $-10, -6, -2, 2 \\dots$\n\n$$a_2 - a_1 = -6 - (-10) = -6 + 10 = 4$$\n\n$$a_3 - a_2 = -2 - (-6) = -2 + 6 = 4$$\n\n$$a_4 - a_3 = 2 - (-2) = 2 + 2 = 4$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  The given list of numbers forms an AP with common difference  $d' = 4$\n\nThe next 3 terms are **6, 10, 14**\n\nv)  $3, 3 + \\sqrt{2}, 3 + 2\\sqrt{2}, 3 + 3\\sqrt{2} \\dots$\n\n$$a_2 - a_1 = 3 + \\sqrt{2} - 3 = \\sqrt{2}$$\n\n$$a_3 - a_2 = 3 + 2\\sqrt{2} - 3 + \\sqrt{2} = \\sqrt{2}$$\n\n$$a_4 - a_3 = 3 + 3\\sqrt{2} - 3 + 2\\sqrt{2} = \\sqrt{2}$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  The given list of numbers forms an AP with common difference  $d = \\sqrt{2}$\n\nThe next 3 terms are  $3 + 4\\sqrt{2}, 3 + 5\\sqrt{2},$\n\n$$3 + 6\\sqrt{2}$$\n\n(vii)  $0, -4, -8, -12 \\dots$\n\n$$a_2 - a_1 = -4 - 0 = -4$$\n\n$$a_3 - a_2 = -8 - (-4) = -8 + 4 = -4$$\n\n$$a_4 - a_3 = -12 - (-8) = -12 + 8 = -4$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  This is an AP with  $d = -4$\n\nThe next 3 terms are **-16, -20, -24**\n\n(viii)  $-\\frac{1}{2}, -\\frac{1}{2}, -\\frac{1}{2}, -\\frac{1}{2}, \\dots$\n\n$$a_2 - a_1 = -\\frac{1}{2} - \\left(-\\frac{1}{2}\\right) = -\\frac{1}{2} + \\frac{1}{2} = 0$$\n\n$$a_3 - a_2 = -\\frac{1}{2} - \\left(-\\frac{1}{2}\\right) = -\\frac{1}{2} + \\frac{1}{2} = 0$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  This is an AP with 'd' = 0\n\nThe next 3 terms are  $-\\frac{1}{2}, -\\frac{1}{2}, -\\frac{1}{2}$\n\n(ix) 1, 3, 9, 27 \\_\\_\\_\n\n$$a_2 - a_1 = 3 - 1 = 2$$\n\n$$a_3 - a_2 = 9 - 3 = 6$$\n\nHere,  $a_2 - a_1 \\neq a_3 - a_2$\n\nTherefore the given list of numbers does not form an AP.\n\n(x) a, 2a, 3a, 4a \\_\\_\\_\n\n$$a_2 - a_1 = 2a - a = a$$\n\n$$a_3 - a_2 = 3a - 2a = a$$\n\n$$a_4 - a_3 = 4a - 3a = a$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  This is an AP with 'd' = a\n\nThe next 3 terms are 5a, 6a, 7a\n\n(xi) a,  $a^2$ ,  $a^3$ ,  $a^4$  .....\n\n$$a_2 - a_1 = a^2 - a = a(a - 1)$$\n\n$$a_3 - a_2 = a^3 - a^2 = a^2(a - 1)$$\n\nHere,  $a_2 - a_1 \\neq a_3 - a_2$\n\nTherefore the given list of numbers does not form an AP.\n\n(xii)  $\\sqrt{2}, \\sqrt{8}, \\sqrt{18}, \\sqrt{32}$  \\_\\_\\_\n\n$$a_2 - a_1 = \\sqrt{8} - \\sqrt{2} = 2\\sqrt{2} - \\sqrt{2} = \\sqrt{2}$$\n\n$$a_3 - a_2 = \\sqrt{18} - \\sqrt{8} = 3\\sqrt{2} - 2\\sqrt{2} = \\sqrt{2}$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\n$\\therefore$  This is an AP with 'd' =  $\\sqrt{2}$\n\nThe next 3 terms are  $\\sqrt{50}, \\sqrt{72}, \\sqrt{98}$\n\n(xiii)  $\\sqrt{3}, \\sqrt{6}, \\sqrt{9}, \\sqrt{12}$  \\_\\_\\_\n\n$$a_2 - a_1 = \\sqrt{6} - \\sqrt{3}$$\n\n$$a_3 - a_2 = \\sqrt{9} - \\sqrt{6} = 3 - \\sqrt{6}$$\n\nHere,  $a_2 - a_1 \\neq a_3 - a_2$\n\nTherefore the given list of numbers does not form an AP.\n\n(xiv)  $1^1, 3^2, 5^2, 7^2, \\dots$\n\n$$a_2 - a_1 = 3^2 - 1^1 = 9 - 1 = 8$$\n\n$$a_3 - a_2 = 5^2 - 3^2 = 25 - 9 = 16$$\n\nHere,  $a_2 - a_1 \\neq a_3 - a_2$\n\nTherefore the given list of numbers does not form an AP.\n\n(xv)  $1^1, 5^2, 7^2, 73, \\dots$\n\n$$a_2 - a_1 = 5^2 - 1^2 = 25 - 1 = 24$$\n\n$$a_3 - a_2 = 7^2 - 5^2 = 49 - 25 = 24$$\n\n$$a_4 - a_3 = 73 - 7^2 = 73 - 49 = 24$$\n\nHere,  $a_2 - a_1 = a_3 - a_2 = a_4 - a_3$\n\nTherefore the given list of numbers forms an AP with common difference  $d = 24$\n\nThe next 3 terms of this AP are  $73 + 24 = 97, 97 + 24 = 121, 121 + 24 = 145$\n\n### $n^{\\text{th}}$ Term of an AP\n\nThe  $n^{\\text{th}}$  term is  $a_n = a + (n - 1)d$\n\n[  $a$  - first term,  $d$  - c.d. ]\n\n$n^{\\text{th}}$  term from the last  $n$ :  $1 - (n-1)d$  [  $1$  - last term,  $d$  - c.d. ]\n\nExample 3 : Find the 10th term of the AP : 2, 7, 12 ...\n\nSolution :\n\n$$a = 2, d = 7 - 2 = 5 \\text{ and } n = 10$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_{10} = 2 + (10 - 1)5$$\n\n$$a_{10} = 2 + (9)5$$\n\n$$a_{10} = 2 + 45$$\n\n$$a_{10} = 47$$\n\nExample 4 : Which term of the AP: 21, 18, 15 ... is -81? Also, is any term 0? Give reason for your answer.\n\n$$\\text{Solution: } a = 21, d = 18 - 21 = -3 \\text{ and } a_n = -81.$$\n\nNow we have to find 'n'\n\n$$a_n = a + (n - 1)d$$\n\n$$-81 = 21 + (n - 1)(-3) = 21 - 3n + 3$$\n\n$$\\Rightarrow -81 = 24 - 3n$$\n\n$$\\Rightarrow 3n = 24 + 81 = 105$$\n\n$$\\Rightarrow n = 35$$\n\nwhich term is Zero?\n\n$$0 = 21 + (n - 1)(-3)$$\n\n$$= 21 - 3n + 3$$\n\n$$\\Rightarrow 3n = 24$$\n\n$$\\Rightarrow n = 8$$\n\n$\\therefore$  8<sup>th</sup> term is Zero\n\nExample 5: Determine the AP whose 3rd term is 5 and the 7th term is 9.\n\n$$\\text{Solutin: } a + (n - 1)d = a_n$$\n\n$$a + (3 - 1)d = 5$$\n\n$$a + 2d = 5$$\n\n$$a + (7 - 1)d = 9$$\n\n$$a + 6d = 9$$\n\n$$a + 2d = 5$$\n\n$$a + 6d = 9$$\n\n$$-4d = -4$$\n\n$$\\Rightarrow d = 1$$\n\n$$\\Rightarrow a + 2(1) = 5$$\n\n$$\\Rightarrow a + 2 = 5$$\n\n$$\\Rightarrow a = 5 - 2 = 3$$\n\n$$\\Rightarrow a = 3$$\n\n$$\\therefore \\text{AP: } 3, 4, 5, 6, \\dots$$\n\n### Alternate Method:\n\n$$d = \\frac{a_p - a_q}{p - q}$$\n\n$$a_p = a_7; a_q = a_3$$\n\n$$d = \\frac{a_7 - a_3}{7 - 3}$$\n\n$$= \\frac{9 - 5}{7 - 3} = \\frac{4}{4} = 1$$\n\n$$\\therefore d = 1$$\n\n$$a = a_p + (p - 1)d a$$\n\n$$a = a_7 + (7 - 1)1$$\n\n$$a = 9 + (7 - 1)1$$\n\n$$a = 9 + 6 = 3$$\n\n$$\\Rightarrow a = 3$$\n\n$$\\therefore \\text{AP: } 3, 4, 5, 6, \\dots$$\n\nExample 6: Check whether 301 is a term of the list of numbers  \n5, 11, 17, 23 ...\n\n$$\\text{Solution: } a = 5, d = 11 - 5 = 6$$\n\n$$a + (n - 1)d = a_n$$\n\n$$5 + (n - 1)6 = 301$$\n\n$$5 + 6n - 6 = 301$$\n\n$$6n - 1 = 301$$\n\n$$6n = 301 + 1$$\n\n$$6n = 302$$\n\n$$\\Rightarrow n = \\frac{302}{6}$$\n\n$$= \\frac{151}{3}$$\n\nHere  $n$  is not an integer\n\nTherefore 301 is not a term of the list of numbers 5, 11, 17, 13 ...\n\nExample 7: How many two-digit numbers are divisible by 3?\n\nSolution: 12, 15, 18\n\n$$a = 12, d = 3, a_n = 99$$\n\n$$a + (n - 1)d = a_n$$\n\n$$12 + (n - 1)3 = 99$$\n\n$$12 + 3n - 3 = 99 \\Rightarrow 3n + 9 = 99$$\n\n$$\\Rightarrow 3n = 99 - 9$$\n\n$$\\Rightarrow 3n = 90$$\n\n$$\\Rightarrow n = 30$$\n\n$\\therefore$  30, 2-digit numbers are divisible by 3.\n\nExample 8: Find the 11th term from the last term (towards the first term) of the AP: 10, 7, 4, ..., -62.\n\n$$\\text{Solution: } a = 10, d = 7 - 10 = -3, l = -62$$\n\n$$l = a + (n - 1)d$$\n\n$$n^{\\text{th}} \\text{ term from the last} = l - (n - 1)d$$\n\n$$= -62 - (11 - 1)(-3)$$\n\n$$= -62 + 33 - 3$$\n\n$$= -62 + 30$$\n\n$$= -32$$\n\nExample 9: A sum of Rs 1000 is invested at 8% simple interest per year. Calculate the interest at the end of each year. Do these interests form an AP? If so, find the interest at the end of 30 years making use of this fact.\n\n$$\\text{Solution: Simple interest } I = \\frac{PRT}{100}$$\n\n$$\\text{The interest at the end of the 1st year} = \\frac{1000 \\times 8 \\times 1}{100} = \\text{Rs}80$$\n\n$$\\text{The interest at the end of the 2nd year} = \\frac{1000 \\times 8 \\times 2}{100} = \\text{Rs}160$$\n\n$$\\text{the interest at the end of the 3rd year} = \\frac{1000 \\times 8 \\times 3}{100} = \\text{Rs}240$$\n\n$\\therefore$  the terms are 80, 160, 240 ...\n\n$$\\text{Here } a_2 - a_1 = a_3 - a_2 = d = 80$$\n\nIt is an AP with  $d = 80$ ,\n\n$$\\text{The interest at the end of 30 years} = a_{30};$$\n\n$$a = 80, d = 80, n = 30$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_{30} = 80 + (30 - 1)80$$\n\n$$a_{30} = 80 + 29 \\times 80$$\n\n$$a_{30} = 80 + 2320$$\n\n$$a_{30} = \\text{Rs}2400$$\n\nExample 10: In a flower bed, there are 23 rose plants in the first row, 21 in the second, 19 in the third, and so on. There are 5 rose plants in the last row. How many rows are there in the flower bed?\n\nSolution: The number of rose plants in the 1st, 2nd, 3rd... rows are :23, 21, 19 ...\n\n$$\\text{Here } a_2 - a_1 = a_3 - a_2 = -2$$\n\n$\\therefore$  it is an AP.  $a = 23$ ,  $d = -2$ ,  $a_n = 5$ ,  $n = ?$\n\n$$a + (n - 1)d = a_n$$\n\n$$23 + (n - 1)(-2) = 5$$\n\n$$23 - 2n + 2 = 5$$\n\n$$-2n + 25 = 5$$\n\n$$-2n = 5 - 25$$\n\n$$-2n = -20$$\n\n$$n = 10$$\n\nSo, there are 10 rows in the flower bed = **10**.\n\n"
    },
    {
      "section_id": 5,
      "section_type": "example",
      "title": "Exercise 5.1: Writing AP Terms",
      "renderer": "manim",
      "narration": {
        "full_text": "Now, let's practice building APs. In this question, we are given the first term, 'a', and the common difference, 'd'. We need to find the first four terms. For the first case, a is 10 and d is 10. The first term is 10. The second is 10 plus 10, which is 20. The third is 20 plus 10, which is 30. And the fourth is 40. Our AP is 10, 20, 30, 40. What happens if the common difference is zero? Let's see. Here, 'a' is -2 and 'd' is 0. The first term is -2. We add 0 to get the second term, which is still -2. And again, and again. When 'd' is zero, all terms in the AP are the same! The common difference can also be negative or a fraction. Let's quickly look at these two cases. When d is -3, the terms decrease: 4, 1, -2, -5. When d is a fraction like 1/2, the terms increase by that fraction: -1, -1/2, 0, 1/2. Finally, let's see an example with decimals. First term is -1.25 and the common difference is -0.25. Starting with -1.25, we keep subtracting 0.25. The sequence becomes -1.50, -1.75, and -2.00. Simple, isn't it?",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Now, let's practice building APs. In this question, we are given the first term, 'a', and the common difference, 'd'. We need to find the first four terms.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "For the first case, a is 10 and d is 10. The first term is 10. The second is 10 plus 10, which is 20. The third is 20 plus 10, which is 30. And the fourth is 40. Our AP is 10, 20, 30, 40.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "What happens if the common difference is zero? Let's see. Here, 'a' is -2 and 'd' is 0.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "The first term is -2. We add 0 to get the second term, which is still -2. And again, and again. When 'd' is zero, all terms in the AP are the same!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "The common difference can also be negative or a fraction. Let's quickly look at these two cases.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "When d is -3, the terms decrease: 4, 1, -2, -5. When d is a fraction like 1/2, the terms increase by that fraction: -1, -1/2, 0, 1/2.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "Finally, let's see an example with decimals. First term is -1.25 and the common difference is -0.25.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "Starting with -1.25, we keep subtracting 0.25. The sequence becomes -1.50, -1.75, and -2.00. Simple, isn't it?",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "2. Write first four terms of",
            "end_phrase": "are given as follows:"
          },
          "display_text": "Write first four terms of the AP, when the first term 'a' and the common difference 'd' are given as follows:",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$\\text{(i) } a = 10, d = 10$$",
            "end_phrase": "AP are 10, 20, 30, 40"
          },
          "display_text": "$$\\text{(i) } a = 10, d = 10$$\n\n$$a_1 = 10;$$\n\n$$a_2 = a_1 + d = 10 + 10 = 20$$\n\n$$a_3 = a_2 + d = 20 + 10 = 30;$$\n\n$$a_4 = a_3 + d = 30 + 10 = 40$$\n\nThus the first four terms of an AP are 10, 20, 30, 40",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$\\text{(ii) } a = -2, d = 0$$",
            "end_phrase": "$$a_1 = -2;$$"
          },
          "display_text": "(ii) a = -2, d = 0",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_2 = a_1 + d = -2 + 0 = -2$$",
            "end_phrase": "AP are -2, -2, -2, -2,"
          },
          "display_text": "$$a_2 = a_1 + d = -2 + 0 = -2$$\n\n$$a_3 = a_2 + d = -2 + 0 = -2;$$\n\n$$a_4 = a_3 + d = -2 + 0 = -2$$\n\nThus the first four terms of an AP are -2, -2, -2, -2,",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "$$\\text{(iii) } a = 4, d = -3$$",
            "end_phrase": "$$(iv) a = -1, d = \\frac{1}{2}$$"
          },
          "display_text": "* a = 4, d = -3\n* a = -1, d = 1/2",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Thus the first four terms of",
            "end_phrase": "AP are  $-1, -\\frac{1}{2}, 0, \\frac{1}{2}$"
          },
          "display_text": "Thus the first four terms of an AP are 4, 1, -2, -5... and for the other, the first four terms of an AP are -1, -1/2, 0, 1/2",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$(v) a = -1.25, d = -0.25$$",
            "end_phrase": "$$a_1 = -1.25; a_2 = a_1 + d$$"
          },
          "display_text": "(v) a = -1.25, d = -0.25",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_3 = a_2 + d = -1.50 - 0.25",
            "end_phrase": "$-1.25, -1.50, -1.75, -2.00$"
          },
          "display_text": "$$a_3 = a_2 + d = -1.50 - 0.25 = -1.75; a_4 = a_3 + d = -1.75 + 0.25 = -2.00$$\n\nThus the first four terms of an AP are  $-1.25, -1.50, -1.75, -2.00$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "The scene displays 'a = [value]' and 'd = [value]'. The term 'a1' appears with the value of 'a'. Then, '+ d' animates next to it, and the result 'a2' appears. This repeats for a3 and a4, forming a sequence on screen. For a=10, d=10, the sequence 10, 20, 30, 40 builds dynamically. For a=-2, d=0, the animation shows '+0' repeatedly, with the term -2 never changing, emphasizing the concept of a constant sequence. For d=-3 and d=1/2, two sequences animate in parallel to show both decreasing and fractional progressions. For the decimal example, the numbers -1.25, -1.50, -1.75, -2.00 appear sequentially as '- 0.25' animates for each step. The visuals use a clean, modern font against a dark blue background with bright accent colors for the numbers and operations.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.1: Writing AP Terms\", font_size=36).to_edge(UP)\n        intro_text = Text(\"Given: First term 'a' and Common difference 'd'\", font_size=28).next_to(title, DOWN, buff=0.5)\n        task_text = Text(\"Find: First four terms\", font_size=28).next_to(intro_text, DOWN, buff=0.3)\n        \n        self.play(Write(title), run_time=1.5)\n        self.play(FadeIn(intro_text), FadeIn(task_text), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(intro_text), FadeOut(task_text), run_time=0.5)\n        \n        case1_label = Text(\"Case 1:\", font_size=28, color=YELLOW).to_edge(LEFT).shift(UP*2)\n        a_val = MathTex(\"a = 10\", font_size=32).next_to(case1_label, RIGHT, buff=0.5)\n        d_val = MathTex(\"d = 10\", font_size=32).next_to(a_val, RIGHT, buff=0.8)\n        \n        self.play(Write(case1_label), Write(a_val), Write(d_val), run_time=1.0)\n        \n        term1 = MathTex(\"10\", font_size=36, color=GREEN).shift(LEFT*4 + DOWN*0.5)\n        term2 = MathTex(\"20\", font_size=36, color=GREEN).shift(LEFT*1.5 + DOWN*0.5)\n        term3 = MathTex(\"30\", font_size=36, color=GREEN).shift(RIGHT*1 + DOWN*0.5)\n        term4 = MathTex(\"40\", font_size=36, color=GREEN).shift(RIGHT*3.5 + DOWN*0.5)\n        \n        self.play(FadeIn(term1), run_time=0.8)\n        self.play(FadeIn(term2), run_time=0.8)\n        self.play(FadeIn(term3), run_time=0.8)\n        self.play(FadeIn(term4), run_time=0.8)\n        self.wait(0.7)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.40s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        self.play(FadeOut(case1_label), FadeOut(a_val), FadeOut(d_val), \n                  FadeOut(term1), FadeOut(term2), FadeOut(term3), FadeOut(term4), run_time=1.0)\n        \n        case2_label = Text(\"Case 2: d = 0\", font_size=28, color=YELLOW).to_edge(LEFT).shift(UP*2)\n        a_val2 = MathTex(\"a = -2\", font_size=32).next_to(case2_label, RIGHT, buff=0.5)\n        d_val2 = MathTex(\"d = 0\", font_size=32).next_to(a_val2, RIGHT, buff=0.8)\n        \n        self.play(Write(case2_label), Write(a_val2), Write(d_val2), run_time=1.5)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        const_term1 = MathTex(\"-2\", font_size=36, color=ORANGE).shift(LEFT*4 + DOWN*0.5)\n        const_term2 = MathTex(\"-2\", font_size=36, color=ORANGE).shift(LEFT*1.5 + DOWN*0.5)\n        const_term3 = MathTex(\"-2\", font_size=36, color=ORANGE).shift(RIGHT*1 + DOWN*0.5)\n        const_term4 = MathTex(\"-2\", font_size=36, color=ORANGE).shift(RIGHT*3.5 + DOWN*0.5)\n        \n        self.play(FadeIn(const_term1), run_time=0.8)\n        self.play(FadeIn(const_term2), run_time=0.8)\n        self.play(FadeIn(const_term3), run_time=0.8)\n        self.play(FadeIn(const_term4), run_time=0.8)\n        self.wait(1.6)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 4.80s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(case2_label), FadeOut(a_val2), FadeOut(d_val2),\n                  FadeOut(const_term1), FadeOut(const_term2), FadeOut(const_term3), FadeOut(const_term4), run_time=1.0)\n        \n        case3_label = Text(\"Case 3: Negative d\", font_size=26, color=YELLOW).shift(UP*2.5 + LEFT*3)\n        case4_label = Text(\"Case 4: Fraction d\", font_size=26, color=YELLOW).shift(UP*2.5 + RIGHT*3)\n        \n        self.play(Write(case3_label), Write(case4_label), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        a3_val = MathTex(\"a = 4, d = -3\", font_size=24).next_to(case3_label, DOWN, buff=0.3)\n        a4_val = MathTex(\"a = -1, d = 1/2\", font_size=24).next_to(case4_label, DOWN, buff=0.3)\n        \n        self.play(Write(a3_val), Write(a4_val), run_time=1.0)\n        \n        seq3 = MathTex(\"4, 1, -2, -5\", font_size=28, color=RED).shift(LEFT*3 + DOWN*1)\n        seq4 = MathTex(\"-1, -1/2, 0, 1/2\", font_size=28, color=BLUE).shift(RIGHT*3 + DOWN*1)\n        \n        self.play(FadeIn(seq3), FadeIn(seq4), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(case3_label), FadeOut(case4_label), FadeOut(a3_val), FadeOut(a4_val),\n                  FadeOut(seq3), FadeOut(seq4), run_time=1.0)\n        \n        case5_label = Text(\"Case 5: Decimals\", font_size=28, color=YELLOW).to_edge(LEFT).shift(UP*2)\n        a5_val = MathTex(\"a = -1.25\", font_size=32).next_to(case5_label, RIGHT, buff=0.5)\n        d5_val = MathTex(\"d = -0.25\", font_size=32).next_to(a5_val, RIGHT, buff=0.8)\n        \n        self.play(Write(case5_label), Write(a5_val), Write(d5_val), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        dec_term1 = MathTex(\"-1.25\", font_size=32, color=PURPLE).shift(LEFT*4.5 + DOWN*0.5)\n        dec_term2 = MathTex(\"-1.50\", font_size=32, color=PURPLE).shift(LEFT*1.5 + DOWN*0.5)\n        dec_term3 = MathTex(\"-1.75\", font_size=32, color=PURPLE).shift(RIGHT*1.5 + DOWN*0.5)\n        dec_term4 = MathTex(\"-2.00\", font_size=32, color=PURPLE).shift(RIGHT*4.5 + DOWN*0.5)\n        \n        self.play(FadeIn(dec_term1), run_time=0.8)\n        self.play(FadeIn(dec_term2), run_time=0.8)\n        self.play(FadeIn(dec_term3), run_time=0.8)\n        self.play(FadeIn(dec_term4), run_time=0.8)\n        self.wait(1.6)\n        # Hard Sync WARNING: Animation exceeds audio by 4.80s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      }
    },
    {
      "section_id": 6,
      "section_type": "example",
      "title": "Exercise 5.1: Finding 'a' and 'd'",
      "renderer": "manim",
      "narration": {
        "full_text": "This time, we're doing the reverse. We are given an AP and we need to find the first term 'a' and the common difference 'd'. Look at this AP: 3, 1, -1, -3... The first term 'a' is simply the first number in the list, which is 3. To find 'd', we subtract the first term from the second: 1 minus 3 is -2. So, d is -2. Let's try two more. One with negative numbers and one where the terms don't seem to change. In the first case, 'a' is -5. The difference is -1 minus -5, which is 4. In the second case, 'a' is 1/2. The difference is 1/2 minus 1/2, which is 0. Remember, a constant sequence is an AP with a common difference of 0! One last example with decimals: 0.6, 1.7, 2.8, 3.9... The first term 'a' is clearly 0.6. The common difference 'd' is 1.7 minus 0.6, which equals 1.1. And you can see it's consistent.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "This time, we're doing the reverse. We are given an AP and we need to find the first term 'a' and the common difference 'd'.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Look at this AP: 3, 1, -1, -3... The first term 'a' is simply the first number in the list, which is 3. To find 'd', we subtract the first term from the second: 1 minus 3 is -2. So, d is -2.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Let's try two more. One with negative numbers and one where the terms don't seem to change.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "In the first case, 'a' is -5. The difference is -1 minus -5, which is 4. In the second case, 'a' is 1/2. The difference is 1/2 minus 1/2, which is 0. Remember, a constant sequence is an AP with a common difference of 0!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "One last example with decimals: 0.6, 1.7, 2.8, 3.9...",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "The first term 'a' is clearly 0.6. The common difference 'd' is 1.7 minus 0.6, which equals 1.1. And you can see it's consistent.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "3. For the following APs, write",
            "end_phrase": "and the common difference:"
          },
          "display_text": "For the following APs, write the first term and the common difference:",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "i) 3, 1, -1, -3...",
            "end_phrase": "$$d = a_2 - a_1 = 1 - 3 = -2$$"
          },
          "display_text": "i) 3, 1, -1, -3...\n\nThe first term  $a = 3$ ,\n\nCommon difference\n\n$$d = a_2 - a_1 = 1 - 3 = -2$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "ii) -5, -1, 3, 7...",
            "end_phrase": "iii)  $\\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\frac{1}{2}, \\dots$"
          },
          "display_text": "* -5, -1, 3, 7...\n* 1/2, 1/2, 1/2, 1/2...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "The first term  $a = 5$ ,",
            "end_phrase": "$$d = a_2 - a_1 = \\frac{1}{2} - \\frac{1}{2} = 0$$"
          },
          "display_text": "For -5, -1, 3, 7... a = -5, d = 4. For 1/2, 1/2, 1/2... a = 1/2, d = 0.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "iv) 0.6, 1.7, 2.8, 3.9, ...",
            "end_phrase": "The first term  $a = 0.6$ ,"
          },
          "display_text": "iv) 0.6, 1.7, 2.8, 3.9, ...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Common difference\n\n$$d = a_2 - a_1",
            "end_phrase": "= 1.7 - 0.6 = 1.1$$"
          },
          "display_text": "Common difference\n\n$$d = a_2 - a_1 = 1.7 - 0.6 = 1.1$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "Scene displays a sequence of numbers, e.g., '3, 1, -1, -3...'. A box highlights the first number '3', and an arrow points to it with the label 'a = 3'. Then, the first two numbers '3' and '1' are highlighted, and the calculation 'd = 1 - 3 = -2' animates on screen. This process repeats for other examples. For the sequence '-5, -1, 3, 7...', '-5' is identified as 'a', and 'd = -1 - (-5) = 4' is calculated. For '1/2, 1/2, 1/2...', '1/2' is identified as 'a' and 'd = 1/2 - 1/2 = 0' is shown, with a note 'Constant Sequence!'. For the decimal example, '0.6' is boxed as 'a', and the calculation 'd = 1.7 - 0.6 = 1.1' animates clearly. The visual style is direct and educational, with clean typography and smooth transitions.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.1: Finding 'a' and 'd'\", font_size=36).to_edge(UP)\n        subtitle = Text(\"Given an AP, find first term and common difference\", font_size=24).next_to(title, DOWN)\n        self.play(Write(title), run_time=2.0)\n        self.play(FadeIn(subtitle), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(subtitle), run_time=0.5)\n        ap_seq = MathTex(\"3,\", \"1,\", \"-1,\", \"-3\", \"...\").scale(1.2).shift(UP)\n        self.play(Write(ap_seq), run_time=1.5)\n        \n        box_a = SurroundingRectangle(ap_seq[0], color=YELLOW, buff=0.1)\n        label_a = MathTex(\"a = 3\", color=YELLOW).next_to(box_a, DOWN, buff=0.3)\n        self.play(Create(box_a), Write(label_a), run_time=1.0)\n        \n        calc_d = MathTex(\"d = 1 - 3 = -2\").next_to(label_a, DOWN, buff=0.4)\n        self.play(Write(calc_d), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        self.play(FadeOut(ap_seq), FadeOut(box_a), FadeOut(label_a), FadeOut(calc_d), run_time=1.0)\n        \n        intro_text = Text(\"Two more examples:\", font_size=28).shift(UP * 2)\n        self.play(Write(intro_text), run_time=1.5)\n        \n        ex1 = MathTex(\"-5,\", \"-1,\", \"3,\", \"7\", \"...\").scale(0.9).shift(UP * 0.5)\n        ex2 = MathTex(\"1/2,\", \"1/2,\", \"1/2\", \"...\").scale(0.9).shift(DOWN * 1)\n        self.play(Write(ex1), Write(ex2), run_time=2.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(intro_text), run_time=0.3)\n        \n        box1 = SurroundingRectangle(ex1[0], color=GREEN, buff=0.08)\n        label1_a = MathTex(\"a = -5\", color=GREEN, font_size=32).next_to(ex1, RIGHT, buff=0.5)\n        calc1_d = MathTex(\"d = -1 - (-5) = 4\", font_size=32).next_to(label1_a, DOWN, buff=0.2)\n        self.play(Create(box1), Write(label1_a), run_time=1.2)\n        self.play(Write(calc1_d), run_time=1.0)\n        \n        box2 = SurroundingRectangle(ex2[0], color=BLUE, buff=0.08)\n        label2_a = MathTex(\"a = 1/2\", color=BLUE, font_size=32).next_to(ex2, RIGHT, buff=0.5)\n        calc2_d = MathTex(\"d = 1/2 - 1/2 = 0\", font_size=32).next_to(label2_a, DOWN, buff=0.2)\n        note = Text(\"Constant Sequence!\", font_size=24, color=ORANGE).next_to(calc2_d, DOWN, buff=0.2)\n        self.play(Create(box2), Write(label2_a), run_time=1.0)\n        self.play(Write(calc2_d), Write(note), run_time=1.2)\n        self.wait(0.3)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(\n            FadeOut(ex1), FadeOut(ex2), FadeOut(box1), FadeOut(box2),\n            FadeOut(label1_a), FadeOut(calc1_d), FadeOut(label2_a), \n            FadeOut(calc2_d), FadeOut(note), run_time=1.0\n        )\n        \n        decimal_title = Text(\"Decimal Example:\", font_size=28).shift(UP * 2)\n        self.play(Write(decimal_title), run_time=1.0)\n        \n        ap_decimal = MathTex(\"0.6,\", \"1.7,\", \"2.8,\", \"3.9\", \"...\").scale(1.1).shift(UP * 0.5)\n        self.play(Write(ap_decimal), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        box_dec = SurroundingRectangle(ap_decimal[0], color=YELLOW, buff=0.1)\n        label_dec_a = MathTex(\"a = 0.6\", color=YELLOW, font_size=36).next_to(ap_decimal, DOWN, buff=0.5)\n        self.play(Create(box_dec), Write(label_dec_a), run_time=1.5)\n        \n        calc_dec_d = MathTex(\"d = 1.7 - 0.6 = 1.1\", font_size=36).next_to(label_dec_a, DOWN, buff=0.3)\n        self.play(Write(calc_dec_d), run_time=1.5)\n        \n        check_text = Text(\"Consistent!\", font_size=28, color=GREEN).next_to(calc_dec_d, DOWN, buff=0.3)\n        self.play(FadeIn(check_text), run_time=1.0)\n        self.wait(1.0)\n        # Hard Sync WARNING: Animation exceeds audio by 5.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      }
    },
    {
      "section_id": 7,
      "section_type": "example",
      "title": "Exercise 5.1: Is it an AP?",
      "renderer": "manim",
      "narration": {
        "full_text": "For our final exercise, we must first check if a list of numbers is an AP. If it is, we find the common difference 'd' and write the next three terms. Let's compare these two. In the first list, 2, 4, 8, 16, the difference between terms is 2, then 4. Not constant, so it's not an AP. In the second list, the difference is always 1/2. So it *is* an AP. We just keep adding 1/2 to find the next terms: 4, 9/2, and 5. What about a series with square roots, like this one? Don't be afraid, the principle is the same. Let's check the difference. The second term minus the first is root 2. The third minus the second is also root 2. It's an AP! The common difference is root 2. We just continue adding it to get the next three terms. Here's a tricky one: 1 squared, 5 squared, 7 squared, 73... Is this an AP? First, let's calculate the values: 1, 25, 49, 73. Now, find the differences. 25 minus 1 is 24. 49 minus 25 is 24. 73 minus 49 is also 24! It is an AP with d=24. We just add 24 to find the next terms: 97, 121, and 145.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "For our final exercise, we must first check if a list of numbers is an AP. If it is, we find the common difference 'd' and write the next three terms.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Let's compare these two. In the first list, 2, 4, 8, 16, the difference between terms is 2, then 4. Not constant, so it's not an AP. In the second list, the difference is always 1/2. So it *is* an AP. We just keep adding 1/2 to find the next terms: 4, 9/2, and 5.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "What about a series with square roots, like this one? Don't be afraid, the principle is the same.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Let's check the difference. The second term minus the first is root 2. The third minus the second is also root 2. It's an AP! The common difference is root 2. We just continue adding it to get the next three terms.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "Here's a tricky one: 1 squared, 5 squared, 7 squared, 73... Is this an AP?",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "First, let's calculate the values: 1, 25, 49, 73. Now, find the differences. 25 minus 1 is 24. 49 minus 25 is 24. 73 minus 49 is also 24! It is an AP with d=24. We just add 24 to find the next terms: 97, 121, and 145.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "4. Which of the following are",
            "end_phrase": "write three more terms"
          },
          "display_text": "Which of the following are APs? If they form an AP, find the common difference 'd' and write three more terms",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "(i) 2, 4, 8, 16 ...",
            "end_phrase": "$\\frac{9}{2} + \\frac{1}{2} = 5$$"
          },
          "display_text": "i) 2, 4, 8, 16... -> Not an AP. ii) 2, 5/2, 3, 7/2... -> Is an AP, d=1/2. Next terms: 4, 9/2, 5.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "v)  $3, 3 + \\sqrt{2}, 3 + 2\\sqrt{2},",
            "end_phrase": "3 + 3\\sqrt{2} \\dots$"
          },
          "display_text": "v)  $3, 3 + \\sqrt{2}, 3 + 2\\sqrt{2}, 3 + 3\\sqrt{2} \\dots$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Here,  $a_2 - a_1 = a_3 - a_2",
            "end_phrase": "$$3 + 6\\sqrt{2}$$"
          },
          "display_text": "The given list of numbers forms an AP with common difference  $d = \\sqrt{2}$\n\nThe next 3 terms are  $3 + 4\\sqrt{2}, 3 + 5\\sqrt{2}, 3 + 6\\sqrt{2}$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "(xv)  $1^1, 5^2, 7^2, 73, \\dots$",
            "end_phrase": "$$a_2 - a_1 = 5^2 - 1^2 = 25 - 1 = 24$$"
          },
          "display_text": "(xv)  $1^1, 5^2, 7^2, 73, \\dots$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Therefore the given list of numbers",
            "end_phrase": "are  $73 + 24 = 97, 97 + 24 = 121, 121 + 24 = 145$"
          },
          "display_text": "Therefore the given list of numbers forms an AP with common difference  $d = 24$\n\nThe next 3 terms of this AP are  $73 + 24 = 97, 97 + 24 = 121, 121 + 24 = 145$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "Scene starts with the title 'Is it an AP?'. For the first comparison, two lists appear. For '2, 4, 8...', subtractions show '4-2=2' and '8-4=4'. A 'Not Equal' sign flashes and a large red 'X' marks it as 'Not AP'. For '2, 5/2, 3...', subtractions show '5/2 - 2 = 1/2' and '3 - 5/2 = 1/2'. A green checkmark appears with 'd = 1/2'. Then, '+1/2' animates to generate the next three terms. For the square root example, the subtractions are shown clearly, resulting in a constant 'sqrt(2)', which is labeled as 'd'. For the final example, the terms '1^1, 5^2, 7^2' transform into '1, 25, 49'. Then the differences are calculated on screen: '25-1=24', '49-25=24', '73-49=24'. A green checkmark appears with 'd=24', and the next terms are calculated.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Is it an AP?\", font_size=48).to_edge(UP)\n        self.play(Write(title), run_time=2.0)\n        self.wait(3.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        list1 = MathTex(\"2,\", \"4,\", \"8,\", \"16\", font_size=36).shift(UP * 1.5 + LEFT * 3)\n        list2 = MathTex(\"2,\", \"5/2,\", \"3,\", \"7/2\", font_size=36).shift(UP * 1.5 + RIGHT * 3)\n        \n        self.play(FadeIn(list1), FadeIn(list2), run_time=1.0)\n        \n        diff1_1 = MathTex(\"4-2=2\", font_size=28, color=YELLOW).next_to(list1, DOWN, buff=0.3)\n        diff1_2 = MathTex(\"8-4=4\", font_size=28, color=YELLOW).next_to(diff1_1, DOWN, buff=0.2)\n        cross1 = Text(\"X\", font_size=60, color=RED).next_to(list1, DOWN, buff=1.2)\n        \n        diff2_1 = MathTex(\"5/2-2=1/2\", font_size=28, color=YELLOW).next_to(list2, DOWN, buff=0.3)\n        diff2_2 = MathTex(\"3-5/2=1/2\", font_size=28, color=YELLOW).next_to(diff2_1, DOWN, buff=0.2)\n        check2 = Text(\"AP!\", font_size=36, color=GREEN).next_to(list2, DOWN, buff=1.2)\n        d_label = MathTex(\"d=1/2\", font_size=32, color=GREEN).next_to(check2, DOWN, buff=0.2)\n        \n        self.play(Write(diff1_1), Write(diff2_1), run_time=0.8)\n        self.play(Write(diff1_2), Write(diff2_2), run_time=0.8)\n        self.play(FadeIn(cross1), FadeIn(check2), FadeIn(d_label), run_time=0.8)\n        \n        next_terms = MathTex(\"4,\", \"9/2,\", \"5\", font_size=32, color=TEAL).next_to(d_label, DOWN, buff=0.3)\n        self.play(Write(next_terms), run_time=0.6)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        self.play(FadeOut(list1, diff1_1, diff1_2, cross1, list2, diff2_1, diff2_2, check2, d_label, next_terms), run_time=1.0)\n        \n        sqrt_list = MathTex(\"\\\\sqrt{2},\", \"2\\\\sqrt{2},\", \"3\\\\sqrt{2},\", \"4\\\\sqrt{2}\", font_size=40).shift(UP * 1.0)\n        self.play(Write(sqrt_list), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        sqrt_diff1 = MathTex(\"2\\\\sqrt{2}-\\\\sqrt{2}=\\\\sqrt{2}\", font_size=32, color=YELLOW).next_to(sqrt_list, DOWN, buff=0.5)\n        sqrt_diff2 = MathTex(\"3\\\\sqrt{2}-2\\\\sqrt{2}=\\\\sqrt{2}\", font_size=32, color=YELLOW).next_to(sqrt_diff1, DOWN, buff=0.3)\n        \n        self.play(Write(sqrt_diff1), run_time=1.0)\n        self.play(Write(sqrt_diff2), run_time=1.0)\n        \n        sqrt_check = Text(\"AP!\", font_size=36, color=GREEN).next_to(sqrt_diff2, DOWN, buff=0.4)\n        sqrt_d = MathTex(\"d=\\\\sqrt{2}\", font_size=36, color=GREEN).next_to(sqrt_check, DOWN, buff=0.2)\n        \n        self.play(FadeIn(sqrt_check), FadeIn(sqrt_d), run_time=1.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(sqrt_list, sqrt_diff1, sqrt_diff2, sqrt_check, sqrt_d), run_time=1.0)\n        \n        tricky_list = MathTex(\"1^2,\", \"5^2,\", \"7^2,\", \"73\", font_size=40).shift(UP * 1.0)\n        self.play(Write(tricky_list), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        values = MathTex(\"1,\", \"25,\", \"49,\", \"73\", font_size=40, color=ORANGE).next_to(tricky_list, DOWN, buff=0.5)\n        self.play(Transform(tricky_list.copy(), values), run_time=1.0)\n        self.play(FadeIn(values), run_time=0.5)\n        \n        calc1 = MathTex(\"25-1=24\", font_size=32, color=YELLOW).next_to(values, DOWN, buff=0.4)\n        calc2 = MathTex(\"49-25=24\", font_size=32, color=YELLOW).next_to(calc1, DOWN, buff=0.2)\n        calc3 = MathTex(\"73-49=24\", font_size=32, color=YELLOW).next_to(calc2, DOWN, buff=0.2)\n        \n        self.play(Write(calc1), run_time=0.6)\n        self.play(Write(calc2), run_time=0.6)\n        self.play(Write(calc3), run_time=0.6)\n        \n        final_check = Text(\"AP!\", font_size=36, color=GREEN).next_to(calc3, DOWN, buff=0.3)\n        final_d = MathTex(\"d=24\", font_size=36, color=GREEN).next_to(final_check, RIGHT, buff=0.3)\n        final_terms = MathTex(\"97, 121, 145\", font_size=32, color=TEAL).next_to(final_check, DOWN, buff=0.3)\n        \n        self.play(FadeIn(final_check), FadeIn(final_d), run_time=0.8)\n        self.play(Write(final_terms), run_time=0.8)\n        self.wait(0.2)\n        # Hard Sync WARNING: Animation exceeds audio by 5.10s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      }
    },
    {
      "section_id": 8,
      "section_type": "content",
      "title": "Exercise 5.2: Fill in the Blanks",
      "renderer": "manim",
      "narration": {
        "full_text": "Alright students, let's tackle Exercise 5.2. Our first task is to fill in the blanks in this table. We are given the first term 'a', the common difference 'd', and the term number 'n'. We need to find the nth term, 'a_n', or sometimes one of the other missing values. It's like making a perfect chai - you need all the right ingredients in the right amounts! For the first row, 'a' is 7, 'd' is 3, and 'n' is 8. We use our master formula, a_n equals a plus (n minus 1) times d. Plugging in the values, we get 7 plus (8 minus 1) times 3, which simplifies to 7 plus 21, giving us 28. Good. Now for the second row. This time, we know 'a' is -18, 'n' is 10, and the nth term 'a_n' is 0. We need to find the common difference 'd'. We set up the equation: 0 equals -18 plus (10 minus 1) times d. This simplifies to 0 equals -18 plus 9d. A little rearrangement tells us 9d equals 18, so 'd' must be 2. Moving on to the third row. Here, we are missing the first term 'a'. We know 'd' is -3, 'n' is 18, and 'a_n' is -5. Our equation becomes -5 equals 'a' plus (18 minus 1) times -3. This is 'a' minus 51. So, to find 'a', we add 51 to -5, which gives us 46. Fourth row! We have 'a' as -18.9, 'd' as 2.5, and 'a_n' as 3.6. Our mission is to find 'n', the number of terms. This is like figuring out how many stops the Bangalore local train makes before reaching your destination! The equation is 3.6 equals -18.9 plus (n minus 1) times 2.5. After distributing and combining terms, we get 2.5n equals 25. Dividing 25 by 2.5 gives us n equals 10. Last one for this table. For row five, 'a' is 3.5, 'd' is 0, and 'n' is a large 105. We need to find 'a_n'. Remember, when the common difference 'd' is zero, every term is the same as the first term! The calculation confirms this: 'a_n' is 3.5 plus (105 minus 1) times 0, which is simply 3.5.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Alright students, let's tackle Exercise 5.2. Our first task is to fill in the blanks in this table. We are given the first term 'a', the common difference 'd', and the term number 'n'. We need to find the nth term, 'a_n', or sometimes one of the other missing values. It's like making a perfect chai - you need all the right ingredients in the right amounts!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "For the first row, 'a' is 7, 'd' is 3, and 'n' is 8. We use our master formula, a_n equals a plus (n minus 1) times d. Plugging in the values, we get 7 plus (8 minus 1) times 3, which simplifies to 7 plus 21, giving us 28.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Good. Now for the second row. This time, we know 'a' is -18, 'n' is 10, and the nth term 'a_n' is 0. We need to find the common difference 'd'.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "We set up the equation: 0 equals -18 plus (10 minus 1) times d. This simplifies to 0 equals -18 plus 9d. A little rearrangement tells us 9d equals 18, so 'd' must be 2.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "Moving on to the third row. Here, we are missing the first term 'a'. We know 'd' is -3, 'n' is 18, and 'a_n' is -5.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "Our equation becomes -5 equals 'a' plus (18 minus 1) times -3. This is 'a' minus 51. So, to find 'a', we add 51 to -5, which gives us 46.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "Fourth row! We have 'a' as -18.9, 'd' as 2.5, and 'a_n' as 3.6. Our mission is to find 'n', the number of terms. This is like figuring out how many stops the Bangalore local train makes before reaching your destination!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "The equation is 3.6 equals -18.9 plus (n minus 1) times 2.5. After distributing and combining terms, we get 2.5n equals 25. Dividing 25 by 2.5 gives us n equals 10.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_9",
            "text": "Last one for this table. For row five, 'a' is 3.5, 'd' is 0, and 'n' is a large 105. We need to find 'a_n'.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_10",
            "text": "Remember, when the common difference 'd' is zero, every term is the same as the first term! The calculation confirms this: 'a_n' is 3.5 plus (105 minus 1) times 0, which is simply 3.5.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "## EXERCISE 5.2\n\n1. Fill in",
            "end_phrase": "the  $n$ th term of the AP: v"
          },
          "display_text": "Fill in the blanks in the following table, given that a is the first term, d the common difference and an the n th term of the AP.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$(i) a_8 = 7 + (8",
            "end_phrase": "$$= 28$$"
          },
          "display_text": "(i) a_8 = 7 + (8 - 1)3 = 7 + 7 * 3 = 7 + 21 = 28",
          "latex_content": "a_8 = 7 + (8 - 1)3 = 7 + 21 = 28",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "| (ii)  | -18   | -",
            "end_phrase": "| 0     |"
          },
          "display_text": "Given a = -18, n = 10, a_n = 0. Find d.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$(ii) 0 = -18 + (10",
            "end_phrase": "$$\\Rightarrow d = 2$$"
          },
          "display_text": "(ii) 0 = -18 + (10 - 1)d => 9d = 18 => d = 2",
          "latex_content": "0 = -18 + (10 - 1)d \\Rightarrow 9d = 18 \\Rightarrow d = 2",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "| (iii) | -     | -3",
            "end_phrase": "| -5    |"
          },
          "display_text": "Given d = -3, n = 18, a_n = -5. Find a.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$(iii) -5 = a + (18",
            "end_phrase": "$$\\Rightarrow a = 46$$"
          },
          "display_text": "(iii) -5 = a + (18 - 1)(-3) => -5 = a - 51 => a = 46",
          "latex_content": "-5 = a + (18 - 1)(-3) \\Rightarrow -5 = a - 51 \\Rightarrow a = 46",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "| (iv)  | -18.9 | 2.5",
            "end_phrase": "| 3.6   |"
          },
          "display_text": "Given a = -18.9, d = 2.5, a_n = 3.6. Find n.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$(iv) 3.6 = -18.9 + (n",
            "end_phrase": "$$\\Rightarrow n = 10$$"
          },
          "display_text": "(iv) 3.6 = -18.9 + (n - 1)(2.5) => 2.5n = 25 => n = 10",
          "latex_content": "3.6 = -18.9 + (n - 1)(2.5) \\Rightarrow 2.5n = 3.6 + 21.4 \\Rightarrow n = \\frac{25}{2.5} = 10",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_9",
          "segment_id": "seg_9",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "| (v)   | 3.5   | 0",
            "end_phrase": "| -     |"
          },
          "display_text": "Given a = 3.5, d = 0, n = 105. Find a_n.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_10",
          "segment_id": "seg_10",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$(v) a_n = 3.5 + (105",
            "end_phrase": "$$\\Rightarrow a_n = 3.5$$"
          },
          "display_text": "(v) a_n = 3.5 + (105 - 1)(0) = 3.5",
          "latex_content": "a_n = 3.5 + (105 - 1)(0) \\Rightarrow a_n = 3.5",
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "Scene opens with a 5x5 grid table appearing, matching the source markdown. The header row is 'a', 'd', 'n', 'a_n'. The table populates with the given values, leaving blanks for the answers. For the first problem, Row (i) glows bright yellow. The formula `a_n = a + (n-1)d` writes itself out in a clean font. The values `a=7`, `d=3`, `n=8` are pulled from the table and substitute themselves into the formula. The calculation `7 + (7) * 3` animates, showing the multiplication first to get `7 + 21`, then the addition to get `28`. The number `28` then animates and flies into the blank space in the table. This process repeats for each of the five rows, highlighting the current row, showing the formula, substituting the known values, and animating the algebraic solution to find the missing variable. For each step, the corresponding numbers from the table slide into place in the equation.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.2: Fill in the Blanks\", font_size=36).to_edge(UP)\n        self.play(Write(title), run_time=1.5)\n        \n        table_data = [\n            [\"a\", \"d\", \"n\", \"a_n\"],\n            [\"7\", \"3\", \"8\", \"?\"],\n            [\"-18\", \"?\", \"10\", \"0\"],\n            [\"?\", \"-3\", \"18\", \"-5\"],\n            [\"-18.9\", \"2.5\", \"?\", \"3.6\"],\n            [\"3.5\", \"0\", \"105\", \"?\"]\n        ]\n        \n        table = Table(\n            table_data,\n            include_outer_lines=True,\n            line_config={\"stroke_width\": 1}\n        ).scale(0.5).next_to(title, DOWN, buff=0.5)\n        \n        self.play(Create(table), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        row1 = table.get_rows()[1]\n        self.play(row1.animate.set_color(YELLOW), run_time=0.5)\n        \n        formula = MathTex(\"a_n\", \"=\", \"a\", \"+\", \"(n-1)\", \"d\").shift(DOWN * 2)\n        self.play(Write(formula), run_time=1.5)\n        \n        calc = MathTex(\"a_8\", \"=\", \"7\", \"+\", \"(8-1)\", \"\\\\times\", \"3\").next_to(formula, DOWN)\n        self.play(Write(calc), run_time=1.0)\n        \n        calc2 = MathTex(\"=\", \"7\", \"+\", \"21\", \"=\", \"28\").next_to(calc, DOWN)\n        self.play(Write(calc2), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        self.play(\n            FadeOut(formula), FadeOut(calc), FadeOut(calc2),\n            row1.animate.set_color(WHITE),\n            run_time=0.5\n        )\n        \n        row2 = table.get_rows()[2]\n        self.play(row2.animate.set_color(YELLOW), run_time=0.5)\n        \n        formula2 = MathTex(\"a_n\", \"=\", \"a\", \"+\", \"(n-1)\", \"d\").shift(DOWN * 2)\n        self.play(Write(formula2), run_time=1.5)\n        \n        setup = MathTex(\"0\", \"=\", \"-18\", \"+\", \"(10-1)\", \"d\").next_to(formula2, DOWN)\n        self.play(Write(setup), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        step1 = MathTex(\"0\", \"=\", \"-18\", \"+\", \"9d\").next_to(setup, DOWN)\n        self.play(Write(step1), run_time=1.5)\n        \n        step2 = MathTex(\"9d\", \"=\", \"18\").next_to(step1, DOWN)\n        self.play(Write(step2), run_time=1.5)\n        \n        answer2 = MathTex(\"d\", \"=\", \"2\").next_to(step2, DOWN)\n        self.play(Write(answer2), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(\n            FadeOut(formula2), FadeOut(setup), FadeOut(step1), FadeOut(step2), FadeOut(answer2),\n            row2.animate.set_color(WHITE),\n            run_time=0.5\n        )\n        \n        row3 = table.get_rows()[3]\n        self.play(row3.animate.set_color(YELLOW), run_time=0.5)\n        \n        formula3 = MathTex(\"a_n\", \"=\", \"a\", \"+\", \"(n-1)\", \"d\").shift(DOWN * 2)\n        self.play(Write(formula3), run_time=1.5)\n        \n        setup3 = MathTex(\"-5\", \"=\", \"a\", \"+\", \"(18-1)\", \"\\\\times\", \"(-3)\").next_to(formula3, DOWN)\n        self.play(Write(setup3), run_time=2.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        step3 = MathTex(\"-5\", \"=\", \"a\", \"-\", \"51\").next_to(setup3, DOWN)\n        self.play(Write(step3), run_time=1.5)\n        \n        answer3 = MathTex(\"a\", \"=\", \"46\").next_to(step3, DOWN)\n        self.play(Write(answer3), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(\n            FadeOut(formula3), FadeOut(setup3), FadeOut(step3), FadeOut(answer3),\n            row3.animate.set_color(WHITE),\n            run_time=0.5\n        )\n        \n        row4 = table.get_rows()[4]\n        self.play(row4.animate.set_color(YELLOW), run_time=0.5)\n        \n        formula4 = MathTex(\"a_n\", \"=\", \"a\", \"+\", \"(n-1)\", \"d\").shift(DOWN * 2)\n        self.play(Write(formula4), run_time=1.5)\n        \n        setup4 = MathTex(\"3.6\", \"=\", \"-18.9\", \"+\", \"(n-1)\", \"\\\\times\", \"2.5\").next_to(formula4, DOWN)\n        self.play(Write(setup4), run_time=2.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        step4 = MathTex(\"3.6\", \"=\", \"-18.9\", \"+\", \"2.5n\", \"-\", \"2.5\").next_to(setup4, DOWN)\n        self.play(Write(step4), run_time=1.5)\n        \n        step5 = MathTex(\"2.5n\", \"=\", \"25\").next_to(step4, DOWN)\n        self.play(Write(step5), run_time=1.5)\n        \n        answer4 = MathTex(\"n\", \"=\", \"10\").next_to(step5, DOWN)\n        self.play(Write(answer4), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 9 (40.0s - 45.0s, duration 5.0s)\n        self.play(\n            FadeOut(formula4), FadeOut(setup4), FadeOut(step4), FadeOut(step5), FadeOut(answer4),\n            row4.animate.set_color(WHITE),\n            run_time=0.5\n        )\n        \n        row5 = table.get_rows()[5]\n        self.play(row5.animate.set_color(YELLOW), run_time=0.5)\n        \n        formula5 = MathTex(\"a_n\", \"=\", \"a\", \"+\", \"(n-1)\", \"d\").shift(DOWN * 2)\n        self.play(Write(formula5), run_time=1.5)\n        \n        setup5 = MathTex(\"a_{105}\", \"=\", \"3.5\", \"+\", \"(105-1)\", \"\\\\times\", \"0\").next_to(formula5, DOWN)\n        self.play(Write(setup5), run_time=2.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 10 (45.0s - 50.0s, duration 5.0s)\n        step6 = MathTex(\"a_{105}\", \"=\", \"3.5\", \"+\", \"0\").next_to(setup5, DOWN)\n        self.play(Write(step6), run_time=1.5)\n        \n        answer5 = MathTex(\"a_{105}\", \"=\", \"3.5\").next_to(step6, DOWN)\n        self.play(Write(answer5), run_time=2.0)\n        self.wait(1.5)\n        # Hard Sync WARNING: Animation exceeds audio by 5.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      },
      "content": "## EXERCISE 5.2\n\n1. Fill in the blanks in the following table, given that  $a$  is the first term,  $d$  the common difference and  $a_n$  the  $n$ th term of the AP: v\n\n|       | a     | d   | n   | $a_n$ |\n|-------|-------|-----|-----|-------|\n| (i)   | 7     | 3   | 8   | -     |\n| (ii)  | -18   | -   | 10  | 0     |\n| (iii) | -     | -3  | 18  | -5    |\n| (iv)  | -18.9 | 2.5 | -   | 3.6   |\n| (v)   | 3.5   | 0   | 105 | -     |\n\n| answer |\n|--------|\n| 28     |\n| 2      |\n| 46     |\n| 10     |\n| 3.5    |\n\n$$a_n = a + (n - 1)d$$\n\n$$(i) a_8 = 7 + (8 - 1)3$$\n\n$$= 7 + 7 \\times 3$$\n\n$$= 7 + 21$$\n\n$$= 28$$\n\n$$(ii) 0 = -18 + (10 - 1)d$$\n\n$$= -18 + 9d$$\n\n$$\\Rightarrow 9d = 18$$\n\n$$\\Rightarrow d = 2$$\n\n$$(iii) -5 = a + (18 - 1)(-3)$$\n\n$$-5 = a - 17 \\times 3$$\n\n$$\\Rightarrow -5 = a - 51$$\n\n$$\\Rightarrow a = 46$$\n\n$$(iv) 3.6 = -18.9 + (n - 1)(2.5)$$\n\n$$\\Rightarrow 3.6 = -18.9 + 2.5n - 2.5$$\n\n$$\\Rightarrow 3.6 = -21.4 + 2.5n$$\n\n$$\\Rightarrow 2.5n = 3.6 + 21.4$$\n\n$$\\Rightarrow n = \\frac{25}{2.5} = \\frac{250}{25}$$\n\n$$\\Rightarrow n = 10$$\n\n$$(v) a_n = 3.5 + (105 - 1)(0)$$\n\n$$= 3.5 + 104 \\times 0$$\n\n$$\\Rightarrow a_n = 3.5$$\n\n2. Choose the correct choice in the following and justify :\n\n(i) 30th term of the AP: 10, 7, 4, ..., is\n\n(A)\n\n97\n\n(B) 77\n\n(C) -77\n\n(D) -87\n\n$$a_n = a + (n - 1)d; d = a_2 - a_1 = 7 - 10 = -3$$\n\n$$a_{30} = 10 + (30 - 1)(-3)$$\n\n$$= 10 + (29)(-3)$$\n\n$$= 10 - 87$$\n\n$$\\Rightarrow a_{30} = -77$$\n\n(ii) 11th term of an AP:  $-3, -\\frac{1}{2}, 2, \\dots$  is\n\n(A) 28\n\n(B) 22\n\n(C) -38\n\n(D)  $-48\\frac{1}{2}$\n\n$$a_n = a + (n - 1)d; d = a_2 - a_1 = -\\frac{1}{2} - (-3) = -\\frac{1}{2} + 3 = \\frac{5}{2}$$\n\n$$a_{11} = -3 + (11 - 1) \\left[ \\frac{5}{2} \\right]$$\n\n$$= -3 + (10) \\left[ \\frac{5}{2} \\right]$$\n\n$$= -3 + 25$$\n\n$$\\Rightarrow a_{11} = 22$$\n\n4. Which term of the AP 3, 8, 13, 18 ... is 78 ?\n\n$$\\text{Solution: } a_n = a + (n - 1)d$$\n\n$$d = 5; a = 3; a_n = 78; n = ?$$\n\n$$78 = 3 + (n - 1)5$$\n\n$$= 3 + 5n - 5$$\n\n$$\\Rightarrow 78 = 5n - 2$$\n\n$$\\Rightarrow 5n = 78 + 2$$\n\n$$\\Rightarrow 5n = 80$$\n\n$$\\Rightarrow n = 16$$\n\n5. Find the number of terms in each of the following APs :\n\ni) 7, 13, 19 \\_\\_\\_ 205\n\n(ii) 18, 15  $\\frac{1}{2}$\n\n13 \\_\\_\\_ -4\n\ni) 7, 13, 19 ... ...\n\n$$205$$\n\n$$a_n = a + (n - 1)d$$\n\n$$d = 6; a = 7; a_n = 205; n = ?$$\n\n$$205 = 7 + (n - 1)6$$\n\n$$205 = 7 + 6n - 6$$\n\n$$205 = 6n + 1$$\n\n$$6n = 205 - 1$$\n\n$$6n = 204$$\n\n$$\\Rightarrow n = \\frac{204}{6}$$\n\n$$\\Rightarrow \\mathbf{n = 34}$$\n\n$$\\text{(iii) } 18, 15\\frac{1}{2}, 13, \\dots, -47$$\n\n$$a_n = a + (n - 1)d$$\n\n$$d = -\\frac{5}{2}; a = 18; a_n = -47; n = ?$$\n\n$$-47 = 18 + (n - 1) \\left[ -\\frac{5}{2} \\right]$$\n\n$$-47 = 18 - \\frac{5}{2}n + \\frac{5}{2} = \\frac{36 - 5n + 5}{2}$$\n\n$$\\Rightarrow -47 = \\frac{41 - 5n}{2}$$\n\n$$\\Rightarrow -94 = 41 - 5n$$\n\n$$-5n = -94 - 41 = -135$$\n\n$$\\Rightarrow n = 27$$\n\n6. Check whether **-150** is a term of the AP: 11, 8, 5, 2 ...\n\n$$\\text{Solution: } a_n = a + (n - 1)d$$\n\n$$d = a_2 - a_1 = -3; a = 11; a_n = 150; n = ?$$\n\n$$-150 = 11 + (n - 1)(-3)$$\n\n$$-150 = 11 - 3n + 3$$\n\n$$-150 = 14 - 3n$$\n\n$$-3n = -150 - 14 = -164$$\n\n$$n = \\frac{164}{3}$$\n\n'n' is not an integer. So, -150 is not a term of the AP: 11, 8, 5, 2, ...\n\n7. Find the 31st term of an AP whose 11th term is 38 and the 16th term is 73.\n\n$$\\text{Solution: } a_n = a + (n - 1)d$$\n\n$$a_{11} = 38, a_{16} = 73, a_{31} = ?$$\n\n$$a + (11 - 1)d = 38$$\n\n$$a + 10d = 38$$\n\n$$a + (16 - 1)d = 73$$\n\n$$a + 15d = 73$$\n\nfrom (1) and (2)\n\n$$\\mathbf{a + 10d = 38}$$\n\n$$\\mathbf{a + 15d = 73}$$\n\n$$-5d = -35$$\n\n$$d = \\frac{-45}{-3} = 7$$\n\n$$(1) \\Rightarrow a + 10 \\times 7 = 38$$\n\n$$\\Rightarrow a + 70 = 38$$\n\n$$\\Rightarrow a = 38 - 70$$\n\n$$\\Rightarrow a = -32$$\n\n$$a_{31} = -32 + (31 - 1)7$$\n\n$$a_{31} = -32 + (30)7$$\n\n$$a_{31} = -32 + 210$$\n\n$$\\mathbf{a_{31} = 178}$$\n\n### **Alternate Method:**\n\n$$d = \\frac{a_p - a_q}{p - q}$$\n\n$$a_p = a_{16}; a_q = a_{11}$$\n\n$$d = \\frac{a_{16} - a_{11}}{16 - 11} = \\frac{73 - 38}{5} = \\frac{35}{5} = 7$$\n\n$$a_n = a_p + (n - p)d$$\n\n$$a_{31} = a_{16} + (31 - 16)7$$\n\n$$a_{31} = 73 + (15)7$$\n\n$$a_{31} = 73 + 105$$\n\n$$= 178$$\n\n8. An AP consists of 50 terms of which 3rd term is 12 and the last term is 106. Find the 29th term. 50\n\n$$a + (n - 1)d = a_n$$\n\n$$n = 50, a_3 = 12, a_n = 106$$\n\n$$a + (50 - 1)d = 106$$\n\n$$a + 49d = 106$$\n\n$$a + 2d = 12$$\n\n$$\\mathbf{a + 49d = 106}$$\n\n$$\\mathbf{a + 2d = 12}$$\n\n$$47d = 94$$\n\n$$\\Rightarrow d = 2$$\n\n$$\\text{eqn (2)} \\Rightarrow a + 2(2) = 12$$\n\n$$a + 4 = 12$$\n\n$$a = 12 - 4 = 8$$\n\n$$a_{29} = 8 + (29 - 1)2$$\n\n$$a_{29} = 8 + (28)2$$\n\n$$a_{29} = 8 + 56$$\n\n$$a_{29} = 64$$\n\n### **Alternate Method:**\n\n$$d = \\frac{a_p - a_q}{p - q}; a_p = a_{50}; a_q = a_3$$\n\n$$d = \\frac{a_{50} - a_3}{50 - 3} = \\frac{106 - 12}{47} = \\frac{94}{47} = 2$$\n\n$$a_n = a_p + (n - p)d$$\n\n$$a_{29} = a_3 + (29 - 3)2$$\n\n$$a_{29} = 12 + (26)2$$\n\n$$a_{29} = 12 + 52$$\n\n$$a_{29} = 64$$\n\n9. If the 3rd and the 9th terms of an AP are 4 and -8 respectively, which term of this AP is zero?\n\nSolution:  $a_3 = 4, a_9 = -8$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_3 = a + (3 - 1)d$$\n\n$$4 = a + 2d$$\n\n$$a_9 = a + (9 - 1)d$$\n\n$$-8 = a + 8d$$\n\n(i) - (ii), we get\n\n$$-12 = 6d$$\n\n$$\\Rightarrow d = -2$$\n\n$$4 = a - 4$$\n\n$$a = 8$$\n\nIf  $a_n = 0$ ,\n\n$$a_n = a + (n - 1)d$$\n\n$$0 = 8 + (n - 1)(-2)$$\n\n$$0 = 8 - 2n + 2$$\n\n$$2n = 10$$\n\n$$n = 5$$\n\nSo, the 5<sup>th</sup> term is 0\n\n### Alternate method:\n\n$$d = \\frac{a_p - a_q}{p - q}$$\n\n$$a_p = a_q; a_q = a_3$$\n\n$$d = \\frac{a_9 - a_3}{9 - 3} = \\frac{-8 - 4}{6} = \\frac{-12}{6} = -2$$\n\n$$a = a_p + (p - 1)d$$\n\n$$a = a_9 - (9 - 1)(-2)$$\n\n$$a = -8 - (8)(-2)$$\n\n$$a = -8 + 16 = 8$$\n\n10. The 17<sup>th</sup> term of an AP exceeds its 10<sup>th</sup> term by 7. Find the common difference.\n\nSolution:\n\n$$a_n = a + (n - 1)d$$\n\n$$a_{17} = a + (17 - 1)d$$\n\n$$a_{17} = a + 16d$$\n\n$$\\text{Similarly, } a_{10} = a + 9d$$\n\n$$\\text{But, } a_{17} - a_{10} = 7$$\n\n$$(a + 16d) - (a + 9d) = 7$$\n\n$$7d = 7$$\n\n$$d = 1$$\n\n11. Which term of the AP: 3, 15, 27, 39, ... will be 132 more than its 54<sup>th</sup> term?\n\nSolution: AP: 3, 15, 27, 39...\n\n$$a = 3, d = 12$$\n\n$$a_{54} = a + (54 - 1)d$$\n\n$$\\begin{aligned}a_{54} &= 3 + (53)(12) \\\\a_{54} &= 3 + 636 = 639 \\\\132 + 639 &= 771 \\\\ \\text{Now, } a_n &= 771. \\\\a_n &= a + (n - 1)d \\\\771 &= 3 + (n - 1)12 \\\\768 &= (n - 1)12 \\\\(n - 1) &= 64 \\\\n &= 65 \\\\ \\therefore 65^{\\text{th}} \\text{ term is } 132 \\text{ more than } 5^{\\text{th}} \\text{ term.}\\end{aligned}$$\n\nOr\n\n$n^{\\text{th}}$  term is 132 more than  $54^{\\text{th}}$  term.\n\n$$\\begin{aligned}n &= 54 + \\frac{132}{12} \\\\&= 54 + 11 = 65^{\\text{th}} \\text{ term.}\\end{aligned}$$\n\n12. Two APs have the same common difference. The difference between their **100** th terms is **100**, what is the difference between their 1000 th terms?\n\nSolution: Let the first terms of an AP's be  $a'$  and  $b'$ . Common difference -  $d$   \nFor the first AP,\n\n$$\\begin{aligned}a_{100} &= a + (100 - 1)d \\\\a_{1000} &= a + 99d \\\\a_{1000} &= a + (1000 - 1)d \\\\a_{1000} &= a + 999d\\end{aligned}$$\n\nFor 2<sup>nd</sup> AP,\n\n$$\\begin{aligned}a_{100} &= b + (100 - 1)d \\\\a_{1000} &= b + 99d \\\\a_{1000} &= b + (1000 - 1)d \\\\a_{1000} &= b + 999d\\end{aligned}$$\n\nThe difference of 100<sup>th</sup> terms is 100\n\nThere for  $(a + 99d) - (b + 99d) = 100$\n\n$$a - b = 100$$\n\nThe difference of 1000<sup>th</sup> terms is ?\n\n$$(a + 999d) - (b + 999d) = a - b$$\n\nFrom equation (i),\n\n$$a_1 - a_2 = 100$$\n\nSo, the difference of 1000<sup>th</sup> terms is 100.\n\n13. How many three-digit numbers are divisible by 7?\n\nSolution: The first 3 digit number which is divisible by 7 is  $(a) = 105$  and  $d = 7$\n\nThe last 3 digit number which is divisible by 7 is  $(a_n) = 994$\n\nThere for AP: 105, 112, 119 ... 994\n\n$$\\begin{aligned}a_n &= a + (n - 1)d \\\\994 &= 105 + (n - 1)7 \\Rightarrow 889 = (n - 1)7 \\\\&\\Rightarrow (n - 1) = 127 \\Rightarrow n = 128\\end{aligned}$$\n\nThere for 128 three digit numbers are divisible by 7.\n\nOr\n\nThe 3-digit numbers which are divisible by 7 are 105, 112, 119 ... 994\n\nThese numbers are in AP:\n\n$$a = 105 \\text{ and } d = 7, a_n = 994$$\n\n$$\\Rightarrow a + (n - 1)d = 994$$\n\n$$\\Rightarrow 105 + (n - 1) \\times 7 = 994$$\n\n$$\\Rightarrow 7(n - 1) = 889$$\n\n$$\\Rightarrow n - 1 = 127$$\n\n$$\\Rightarrow n = 128$$\n\n14. How many multiples of 4 lie between 10 and 250?\n\nSolution: Multiples of 4 lie between 10 and 250 are\n\n$$12, 16, 20, 24, \\dots 248$$\n\n$$a = 12, d = 4, a_n = 248$$\n\n$$a_n = a + (n - 1)d$$\n\n$$248 = 12 + (n - 1) \\times 4$$\n\n$$248 = 12 + 4n - 4 = 8 + 4n$$\n\n$$\\Rightarrow 4n = 248 - 8 = 240$$\n\n$$\\Rightarrow n = 60$$\n\nHence, there are 60 multiples of 4 lie between 10 and 250.\n\n15. For what value of  $n$ , are the  $n$ th terms of two APs: 63, 65, 67, ... and 3, 10, 17, ... equal?\n\n$$\\text{Solution: } a = 63, d = a_2 - a_1 = 65 - 63 = 2$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_n = 63 + (n - 1)2 = 63 + 2n - 2$$\n\n$$a_n = 61 + 2n$$\n\n$$3, 10, 17, \\dots [a = 3, d = a_2 - a_1 = 10 - 3 = 7]$$\n\n$$a_n = 3 + (n - 1)7 = 3 + 7n - 7$$\n\n$$a_n = 7n - 4$$\n\nAccording to  $n$ th term of both APs' s are equal.\n\n$$\\Rightarrow 61 + 2n = 7n - 4$$\n\n$$\\Rightarrow 61 + 4 = 5n$$\n\n$$\\Rightarrow 5n = 65$$\n\n$$\\Rightarrow n = 13$$\n\nHence, the 13th the two given APs are equal.\n\n16. Determine the AP whose third term is 16 and the 7th term exceeds the 5th term by 12\n\n$$a_3 = 16 \\Rightarrow a + (3 - 1)d = 16$$\n\n$$a + 2d = 16$$\n\n$$a_7 - a_5 = 12$$\n\n$$[a + (7 - 1)d] - [a + (5 - 1)d] = 12$$\n\n$$(a + 6d) - (a + 4d) = 12$$\n\n$$2d = 12 \\Rightarrow \\mathbf{d = 6}$$\n : From equation (i),\n\n$$a + 2(6) = 16$$\n\n$$\\Rightarrow a + 12 = 16$$\n\n$$\\Rightarrow a = 4$$\n\nThen the AP is 4, 10, 16, 22, ...\n\n17. Find the 20th term from the last term of the AP: 3, 8, 13, ..., 253.\n\nGiven AP: 3, 8, 13, ..., 253\n\n$n^{\\text{th}}$  term from the last  $= l - (n - 1)d$\n\n$$l = 253, a = 3, d = 5$$\n\n$n^{\\text{th}}$  term from the last\n\n$$= 253 - (20 - 1)5$$\n\n$$= 253 - (19)5$$\n\n$$= 253 - 95$$\n\n$$= 253 - 95$$\n\n$$= 158$$\n\n18. The sum of the 4th and 8th terms of an AP is 24 and the sum of the 6th and 10th terms is 44. Find the first three terms of the AP.\n\n$$a_n = a + (n - 1)d$$\n\n$$a_4 = a + (4 - 1)d$$\n\n$$a_4 = a + 3d$$\n\nSimilarly,\n\n$$a_8 = a + 7d; a_6 = a + 5d; a_{10} = a + 9d$$\n\n$$\\text{But, } a_4 + a_8 = 24$$\n\n$$a + 3d + a + 7d = 24$$\n\n$$2a + 10d = 24$$\n\n$$a + 5d = 12$$\n\n$$a_6 + a_{10} = 44$$\n\n$$a + 5d + a + 9d = 44$$\n\n$$2a + 14d = 44$$\n\n$$a + 7d = 22$$\n\nBy subtracting (ii) from (i),\n\n$$2d = 22 - 12 = 10$$\n\n$$d = 5$$\n\nSubstituting  $d = 5$  in equation (i),\n\n$$a + 5d = 12$$\n\n$$a + 5(5) = 12$$\n\n$$a + 25 = 12$$\n\n$$a = -13$$\n\n$$a_2 = a + d = -13 + 5 = -8$$\n\n$$a_3 = a_2 + d = -8 + 5 = -3$$\n\nHence the first three terms are  \n-13, -8, and -3.\n\n19. Subbia Rao started work in 1995 at an annual salary of Rs 5000 and received an increment of Rs 200 each year. In which year did his income reach Rs 7000?\n\nThe annual salary received by Subba Rao in the years 1995 onwards are  \n5000, 5200, 5400, ..., 7000\n\nHence, these numbers forms an AP.\n\n$$a = 5000, d = 200, a_n = 7000.$$\n\n$$\\begin{aligned}a_n &= a + (n - 1)d \\\\ 7000 &= 5000 + (n - 1)200 \\\\ 200(n - 1) &= 2000 \\\\ (n - 1) &= 10 \\\\ n &= 11\\end{aligned}$$\n\nThus the 11<sup>th</sup> years of his service or in 2005, Subba Rao received an annual salary of Rs 7000.\n\n20. Ramkali saved Rs 5 in the first week of a year and then increased her weekly savings by Rs 1.75. If in the nth week, her weekly savings become Rs 20.75, find n.\n\nSolution:\n\n$$\\begin{aligned}a &= 5, d = 1.75, a_n = 20.75, n = ? \\\\ a_n &= a + (n - 1)d \\\\ 20.75 &= 5 + (n - 1) \\times 1.75 \\\\ 15.75 &= (n - 1) \\times 1.75 \\\\ 15.75 &= 1.75n - 1.75 \\\\ 1.75n &= 15.75 + 1.75 \\\\ 1.75n &= 17.50 \\\\ n &= \\frac{17.50}{1.75} = \\frac{1750}{175} \\\\ n &= 10\\end{aligned}$$\n\n"
    },
    {
      "section_id": 9,
      "section_type": "quiz",
      "title": "Choose the Correct Choice",
      "renderer": "none",
      "narration": {
        "full_text": "Now for a quick challenge. Let's test your skills. Question 2, part one: What is the 30th term of the AP: 10, 7, 4, and so on? Your options are (A) 97, (B) 77, (C) -77, (D) -87.<pause duration='4'/>The correct answer is (C) -77! Here, the first term 'a' is 10 and the common difference 'd' is -3. So, a_30 is 10 plus 29 times -3, which is 10 minus 87, resulting in -77.Ready for the next one? Part two: What is the 11th term of the AP: -3, -1/2, 2, and so on? Is it (A) 28, (B) 22, (C) -38, or (D) -48 and a half?<pause duration='4'/>And the answer is (B) 22! The first term 'a' is -3, and the common difference 'd' is 5/2. So, a_11 is -3 plus 10 times 5/2. This simplifies to -3 plus 25, which gives us 22. Well done!",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Now for a quick challenge. Let's test your skills. Question 2, part one: What is the 30th term of the AP: 10, 7, 4, and so on? Your options are (A) 97, (B) 77, (C) -77, (D) -87.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "<pause duration='4'/>",
            "purpose": "emphasize",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "The correct answer is (C) -77! Here, the first term 'a' is 10 and the common difference 'd' is -3. So, a_30 is 10 plus 29 times -3, which is 10 minus 87, resulting in -77.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Ready for the next one? Part two: What is the 11th term of the AP: -3, -1/2, 2, and so on? Is it (A) 28, (B) 22, (C) -38, or (D) -48 and a half?",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "<pause duration='4'/>",
            "purpose": "emphasize",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "And the answer is (B) 22! The first term 'a' is -3, and the common difference 'd' is 5/2. So, a_11 is -3 plus 10 times 5/2. This simplifies to -3 plus 25, which gives us 22. Well done!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_11",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "2. Choose the correct choice in",
            "end_phrase": "(D) -87"
          },
          "display_text": "(i) 30th term of the AP: 10, 7, 4, ..., is\n(A) 97\n(B) 77\n(C) -77\n(D) -87",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_12",
          "segment_id": "seg_3",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_{30} = 10 + (30 -",
            "end_phrase": "$$\\Rightarrow a_{30} = -77$$"
          },
          "display_text": "Correct! (C) -77\nCalculation: a_30 = 10 + (30 - 1)(-3) = 10 - 87 = -77",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": true
        },
        {
          "beat_id": "beat_13",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "(ii) 11th term of an AP:",
            "end_phrase": "(D)  $-48\\frac{1}{2}$"
          },
          "display_text": "(ii) 11th term of an AP: -3, -1/2, 2, ... is\n(A) 28\n(B) 22\n(C) -38\n(D) -48 1/2",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_14",
          "segment_id": "seg_6",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "$$a_{11} = -3 + (11 -",
            "end_phrase": "$$\\Rightarrow a_{11} = 22$$"
          },
          "display_text": "Correct! (B) 22\nCalculation: a_11 = -3 + (11 - 1)[5/2] = -3 + 25 = 22",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": true
        }
      ],
      "render_spec": {
        "manim_scene_spec": null,
        "video_prompts": []
      }
    },
    {
      "section_id": 10,
      "section_type": "content",
      "title": "Sum of First n Terms Formula and Examples",
      "renderer": "manim",
      "narration": {
        "full_text": "Now, let's learn how to find the sum of terms in an Arithmetic Progression. Imagine you are saving money for Diwali. You save 10 rupees on day one, 15 on day two, 20 on day three, and so on. How much will you have after 30 days? Instead of adding each day's savings one by one, we can use a handy formula! We have two main formulas to find the sum, which we call 'S'. The first formula is S equals n by 2, times the quantity 2a plus (n minus 1)d. We use this when we know the first term 'a', the common difference 'd', and the number of terms 'n'. The second formula is simpler: S equals n by 2, times (a plus l). This one is perfect when you know the first term 'a', the last term 'l', and the number of terms 'n'. Let's see these formulas in action with our first example. We need to find the sum of the first 22 terms of the AP: 8, 3, -2, and so on. Here, the first term 'a' is 8, the common difference 'd' is -5, and 'n' is 22. We use our first formula. S equals 22 divided by 2, times [2 times 8, plus (22 minus 1) times -5]. This simplifies to 11 times [16 plus 21 times -5], which is 11 times [16 minus 105]. Finally, we get our sum, which is -979. Now for another one. If the sum of the first 14 terms is 1050, and the first term is 10, we need to find the 20th term. Here, we know S14, n, and a. We can use the sum formula to find 'd'. 1050 equals 14 by 2, times [2 times 10 plus (14 minus 1)d]. This boils down to 1050 equals 7 times [20 plus 13d]. After some calculation, we find that the common difference 'd' is 10. Now that we have 'a' and 'd', we can find any term! To find the 20th term, we use the formula a20 equals a plus (20 minus 1)d. Substituting the values, we get 10 plus 19 times 10, which equals 200. Let's look at a slightly different problem. How many terms of the AP: 24, 21, 18, and so on, must be taken so their sum is 78? Here we know 'a' is 24, 'd' is -3, and the sum Sn is 78. We need to find 'n'. We set up the equation: 78 equals n by 2, times [2 times 24 plus (n minus 1) times -3]. This simplifies to a quadratic equation: n-squared minus 17n plus 52 equals 0. When we factor this, we get (n minus 13) times (n minus 4) equals 0. So, 'n' can be either 4 or 13. Both are correct! The sum of the first 4 terms is 78, and because the terms eventually become negative, the sum of the first 13 terms also happens to be 78. Here's a classic! Let's find the sum of the first 1000 positive integers. That's 1 plus 2 plus 3, all the way to 1000. Using our formula, the sum is 500,500. Now let's generalize this to find the sum of the first 'n' positive integers. The formula simplifies beautifully to S equals n times (n plus 1) all divided by 2. A very useful formula to remember! Let's try another one. Find the sum of the first 24 terms for a list where the nth term is given by a_n equals 3 plus 2n. First, let's find the first few terms to confirm it's an AP. a1 is 5, a2 is 7, a3 is 9. Yes, it's an AP with a=5 and d=2. Now we find the sum of 24 terms using our formula. After substituting the values and calculating, we find the sum is 672. Finally, let's solve a real-world problem. A TV manufacturer produced 600 sets in the third year and 700 in the seventh year. The production increases uniformly, so it's an AP. First, let's find the production in the first year and the rate of increase. We set up two equations: a plus 2d equals 600, and a plus 6d equals 700. Solving these, we find the common difference 'd' is 25, and the first term 'a' is 550. So, the production in the first year was 550 sets. To find the production in the 10th year, we calculate a10, which is 550 plus 9 times 25, giving us 775 sets. Lastly, to find the total production in the first 7 years, we calculate S7. This comes out to be 4375 sets in total. You see how powerful these formulas are!",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Now, let's learn how to find the sum of terms in an Arithmetic Progression. Imagine you are saving money for Diwali. You save 10 rupees on day one, 15 on day two, 20 on day three, and so on. How much will you have after 30 days? Instead of adding each day's savings one by one, we can use a handy formula!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "We have two main formulas to find the sum, which we call 'S'. The first formula is S equals n by 2, times the quantity 2a plus (n minus 1)d. We use this when we know the first term 'a', the common difference 'd', and the number of terms 'n'.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "The second formula is simpler: S equals n by 2, times (a plus l). This one is perfect when you know the first term 'a', the last term 'l', and the number of terms 'n'.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Let's see these formulas in action with our first example. We need to find the sum of the first 22 terms of the AP: 8, 3, -2, and so on.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "Here, the first term 'a' is 8, the common difference 'd' is -5, and 'n' is 22. We use our first formula. S equals 22 divided by 2, times [2 times 8, plus (22 minus 1) times -5].",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "This simplifies to 11 times [16 plus 21 times -5], which is 11 times [16 minus 105]. Finally, we get our sum, which is -979.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "Now for another one. If the sum of the first 14 terms is 1050, and the first term is 10, we need to find the 20th term.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "Here, we know S14, n, and a. We can use the sum formula to find 'd'. 1050 equals 14 by 2, times [2 times 10 plus (14 minus 1)d]. This boils down to 1050 equals 7 times [20 plus 13d]. After some calculation, we find that the common difference 'd' is 10.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_9",
            "text": "Now that we have 'a' and 'd', we can find any term! To find the 20th term, we use the formula a20 equals a plus (20 minus 1)d. Substituting the values, we get 10 plus 19 times 10, which equals 200.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_10",
            "text": "Let's look at a slightly different problem. How many terms of the AP: 24, 21, 18, and so on, must be taken so their sum is 78?",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_11",
            "text": "Here we know 'a' is 24, 'd' is -3, and the sum Sn is 78. We need to find 'n'. We set up the equation: 78 equals n by 2, times [2 times 24 plus (n minus 1) times -3].",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_12",
            "text": "This simplifies to a quadratic equation: n-squared minus 17n plus 52 equals 0. When we factor this, we get (n minus 13) times (n minus 4) equals 0. So, 'n' can be either 4 or 13. Both are correct! The sum of the first 4 terms is 78, and because the terms eventually become negative, the sum of the first 13 terms also happens to be 78.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_13",
            "text": "Here's a classic! Let's find the sum of the first 1000 positive integers. That's 1 plus 2 plus 3, all the way to 1000. Using our formula, the sum is 500,500.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_14",
            "text": "Now let's generalize this to find the sum of the first 'n' positive integers. The formula simplifies beautifully to S equals n times (n plus 1) all divided by 2. A very useful formula to remember!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_15",
            "text": "Let's try another one. Find the sum of the first 24 terms for a list where the nth term is given by a_n equals 3 plus 2n.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_16",
            "text": "First, let's find the first few terms to confirm it's an AP. a1 is 5, a2 is 7, a3 is 9. Yes, it's an AP with a=5 and d=2. Now we find the sum of 24 terms using our formula. After substituting the values and calculating, we find the sum is 672.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_17",
            "text": "Finally, let's solve a real-world problem. A TV manufacturer produced 600 sets in the third year and 700 in the seventh year. The production increases uniformly, so it's an AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_18",
            "text": "First, let's find the production in the first year and the rate of increase. We set up two equations: a plus 2d equals 600, and a plus 6d equals 700. Solving these, we find the common difference 'd' is 25, and the first term 'a' is 550. So, the production in the first year was 550 sets.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_19",
            "text": "To find the production in the 10th year, we calculate a10, which is 550 plus 9 times 25, giving us 775 sets.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_20",
            "text": "Lastly, to find the total production in the first 7 years, we calculate S7. This comes out to be 4375 sets in total. You see how powerful these formulas are!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "## Sum of First n Terms",
            "end_phrase": "of an AP"
          },
          "display_text": "Sum of First n Terms of an AP",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$S = \\frac{n}{2}[2a + (n",
            "end_phrase": "Common difference - } d]$$"
          },
          "display_text": "S = n/2[2a + (n-1)d]",
          "latex_content": "S = \\frac{n}{2}[2a + (n - 1)d]",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$S = \\frac{n}{2}[a + l]",
            "end_phrase": "last term - } l]$$"
          },
          "display_text": "S = n/2[a + l]",
          "latex_content": "S = \\frac{n}{2}[a + l]",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 11: Find the sum of",
            "end_phrase": "the AP: 8, 3, -2, ..."
          },
          "display_text": "Example 11: Find the sum of the first 22 terms of the AP: 8, 3, -2, ...",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "Here  $a = 8$ , ",
            "end_phrase": "S &= \\frac{22}{2}[2 \\times 8 + (22 - 1)(-5)]"
          },
          "display_text": "Given a=8, d=-5, n=22. We calculate S = 22/2 [2*8 + (22-1)(-5)]",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "S &= 11[16 + 21(-5)]",
            "end_phrase": "S &= 11 \\times -89 = -979\\end{aligned}$$"
          },
          "display_text": "S = 11[16 + 21(-5)] = 11[16 - 105] = 11 * -89 = -979",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 12: If the sum of",
            "end_phrase": "10, find the 20th term."
          },
          "display_text": "Example 12: If the sum of the first 14 terms of an AP is 1050 and its first term is 10, find the 20th term.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "Solution: Here, $$S_{14} = 1050, n",
            "end_phrase": "d &= \\frac{910}{91} = 10"
          },
          "display_text": "Given S_14=1050, n=14, a=10. We solve for d to get d=10.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_9",
          "segment_id": "seg_9",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "a_n &= a + (n-1)d",
            "end_phrase": "a_{20} &= 200\\end{aligned}$$"
          },
          "display_text": "a_20 = 10 + (20-1)10 = 10 + 190 = 200",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_10",
          "segment_id": "seg_10",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 13 : How many terms",
            "end_phrase": "their sum is 78 ?"
          },
          "display_text": "Example 13 : How many terms of the AP: 24, 21, 18, ... must be taken so that their sum is 78 ?",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_11",
          "segment_id": "seg_11",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "Solution:  $a = 24, d",
            "end_phrase": "78 &= \\frac{n}{2}[48 - 3n + 3]"
          },
          "display_text": "Given a=24, d=-3, S_n=78. We set up the equation: 78 = n/2 [2*24 + (n-1)(-3)]",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_12",
          "segment_id": "seg_12",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "156 &= n[48 - 3n",
            "end_phrase": "n &= 13 \\text{ OR } n = 4\\end{aligned}$$"
          },
          "display_text": "This simplifies to the quadratic equation n^2 - 17n + 52 = 0, which gives the solutions n=13 or n=4.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_13",
          "segment_id": "seg_13",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 14 : Find the sum",
            "end_phrase": "(i) the first **1000** positive integers"
          },
          "display_text": "Example 14: Find the sum of the first 1000 positive integers.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_14",
          "segment_id": "seg_14",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "(ii) Let  $S = 1",
            "end_phrase": "S = \\frac{n}{2}[n + 1]$$"
          },
          "display_text": "The sum of the first n positive integers is given by the formula S = n(n+1)/2.",
          "latex_content": "S = \\frac{n(n+1)}{2}",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_15",
          "segment_id": "seg_15",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 15: Find the sum of",
            "end_phrase": "given by  $a_n = 3 + 2n$ ."
          },
          "display_text": "Example 15: Find the sum of first 24 terms of the list of numbers whose nth term is given by a_n = 3 + 2n.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_16",
          "segment_id": "seg_16",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "There for AP is : 5,",
            "end_phrase": "S = 672$$"
          },
          "display_text": "AP is: 5, 7, 9,... with a=5, d=2, n=24. The sum S = 672.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_17",
          "segment_id": "seg_17",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "Example 16: A manufacturer of TV",
            "end_phrase": "number every year, find"
          },
          "display_text": "Example 16: A manufacturer of TV sets produced 600 sets in the third year and 700 sets in the seventh year. Assuming that the production increases uniformly by a fixed number every year, find the production details.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_18",
          "segment_id": "seg_18",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "a_3 = 600, a_7 = 700,$$",
            "end_phrase": "d = 25 \\text{ and } a = 550$$"
          },
          "display_text": "From a_3=600 and a_7=700, we solve the equations to find d=25 and a=550.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_19",
          "segment_id": "seg_19",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "(ii) Production of TV sets in",
            "end_phrase": "a_{10} = 550 + 9 \\times 25 = 550 + 225 = 775$$"
          },
          "display_text": "Production in the 10th year: a_10 = 550 + 9 * 25 = 775",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_20",
          "segment_id": "seg_20",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "(iii) The total production of TV",
            "end_phrase": "S &= 4375\\end{aligned}$$"
          },
          "display_text": "Total production in first 7 years: S_7 = 7/2 [2*550 + (7-1)25] = 4375",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "The scene starts with the title 'Sum of First n Terms of an AP'. The two main formulas, S = n/2[2a + (n-1)d] and S = n/2[a+l], appear below the title with clean, modern typography. For each example, the scene transitions to a new slate. For Example 11, the AP '8, 3, -2, ...' is shown. The values 'a=8', 'd=-5', and 'n=22' are extracted and colored. These values are then substituted into the first sum formula, with each substitution animated smoothly. The calculation unfolds step-by-step: 22/2 becomes 11, the bracketed expression is simplified, and the final multiplication reveals the answer -979, which glows briefly. For Example 12, the knowns 'S14=1050' and 'a=10' are displayed. The sum formula is written, and the values are plugged in. The animation shows the algebraic steps to isolate 'd', with terms moving across the equals sign and changing sign, ultimately showing 'd=10'. Then, the nth term formula appears, and the values for a20 are substituted to arrive at '200'. For Example 13, the animation shows the formula being populated and simplified into the quadratic equation n^2 - 17n + 52 = 0. The equation then visually splits into its factors, (n-13) and (n-4), which then solve to show the two possible answers for n. For Example 16, the two initial conditions 'a3=600' and 'a7=700' are presented as a system of linear equations. The animation shows one equation sliding under the other, followed by a subtraction operation that cancels 'a' and solves for 'd'. The value of 'd' is then substituted back to solve for 'a'. Finally, the calculated values for a10 and S7 are displayed clearly.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Sum of First n Terms of an AP\", font_size=40).to_edge(UP)\n        self.play(Write(title), run_time=2.0)\n        savings_text = Text(\"Saving: Rs.10, Rs.15, Rs.20, ...\", font_size=28).shift(UP*0.5)\n        question = Text(\"Total after 30 days?\", font_size=28).next_to(savings_text, DOWN, buff=0.5)\n        self.play(FadeIn(savings_text), run_time=1.5)\n        self.play(FadeIn(question), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(savings_text), FadeOut(question), run_time=0.5)\n        formula1 = MathTex(\"S = \\\\frac{n}{2}[2a + (n-1)d]\", font_size=36).shift(UP*1.0)\n        label1 = Text(\"When you know: a, d, n\", font_size=24, color=YELLOW).next_to(formula1, DOWN, buff=0.3)\n        self.play(Write(formula1), run_time=2.0)\n        self.play(FadeIn(label1), run_time=1.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        formula2 = MathTex(\"S = \\\\frac{n}{2}(a + l)\", font_size=36).next_to(label1, DOWN, buff=0.8)\n        label2 = Text(\"When you know: a, l, n\", font_size=24, color=GREEN).next_to(formula2, DOWN, buff=0.3)\n        self.play(Write(formula2), run_time=2.0)\n        self.play(FadeIn(label2), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(title), FadeOut(formula1), FadeOut(label1), FadeOut(formula2), FadeOut(label2), run_time=1.0)\n        ex1_title = Text(\"Example 1\", font_size=36, color=BLUE).to_edge(UP)\n        ap_seq = MathTex(\"8, 3, -2, ...\", font_size=32).shift(UP*1.5)\n        self.play(Write(ex1_title), run_time=1.5)\n        self.play(Write(ap_seq), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        values = MathTex(\"a = 8, \\\\quad d = -5, \\\\quad n = 22\", font_size=28).next_to(ap_seq, DOWN, buff=0.5)\n        formula_sub = MathTex(\"S = \\\\frac{22}{2}[2(8) + (22-1)(-5)]\", font_size=28).shift(DOWN*0.5)\n        self.play(Write(values), run_time=2.0)\n        self.play(Write(formula_sub), run_time=2.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        step1 = MathTex(\"= 11[16 + 21(-5)]\", font_size=28).next_to(formula_sub, DOWN, buff=0.3)\n        step2 = MathTex(\"= 11[16 - 105]\", font_size=28).next_to(step1, DOWN, buff=0.3)\n        answer1 = MathTex(\"S = -979\", font_size=32, color=GOLD).next_to(step2, DOWN, buff=0.5)\n        self.play(Write(step1), run_time=1.5)\n        self.play(Write(step2), run_time=1.5)\n        self.play(Write(answer1), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(ap_seq), FadeOut(values), FadeOut(formula_sub), FadeOut(step1), FadeOut(step2), FadeOut(answer1), run_time=1.0)\n        ex2_title = Text(\"Example 2\", font_size=36, color=BLUE).to_edge(UP)\n        given = MathTex(\"S_{14} = 1050, \\\\quad a = 10\", font_size=28).shift(UP*1.0)\n        find = Text(\"Find: 20th term\", font_size=28).next_to(given, DOWN, buff=0.5)\n        self.play(Transform(ex1_title, ex2_title), run_time=1.0)\n        self.play(Write(given), run_time=2.0)\n        self.play(Write(find), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        eq1 = MathTex(\"1050 = \\\\frac{14}{2}[2(10) + 13d]\", font_size=26).shift(DOWN*0.3)\n        eq2 = MathTex(\"1050 = 7[20 + 13d]\", font_size=26).next_to(eq1, DOWN, buff=0.3)\n        d_value = MathTex(\"d = 10\", font_size=28, color=YELLOW).next_to(eq2, DOWN, buff=0.5)\n        self.play(Write(eq1), run_time=1.5)\n        self.play(Write(eq2), run_time=1.5)\n        self.play(Write(d_value), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 9 (40.0s - 45.0s, duration 5.0s)\n        self.play(FadeOut(given), FadeOut(find), FadeOut(eq1), FadeOut(eq2), run_time=0.5)\n        term_formula = MathTex(\"a_{20} = a + 19d\", font_size=28).shift(UP*0.5)\n        term_calc = MathTex(\"= 10 + 19(10)\", font_size=28).next_to(term_formula, DOWN, buff=0.3)\n        answer2 = MathTex(\"a_{20} = 200\", font_size=32, color=GOLD).next_to(term_calc, DOWN, buff=0.5)\n        self.play(Write(term_formula), run_time=1.5)\n        self.play(Write(term_calc), run_time=1.5)\n        self.play(Write(answer2), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 10 (45.0s - 50.0s, duration 5.0s)\n        self.play(FadeOut(d_value), FadeOut(term_formula), FadeOut(term_calc), FadeOut(answer2), run_time=1.0)\n        ex3_title = Text(\"Example 3\", font_size=36, color=BLUE).to_edge(UP)\n        ap3 = MathTex(\"24, 21, 18, ...\", font_size=28).shift(UP*1.0)\n        question3 = Text(\"How many terms sum to 78?\", font_size=28).next_to(ap3, DOWN, buff=0.5)\n        self.play(Transform(ex1_title, ex3_title), run_time=1.0)\n        self.play(Write(ap3), run_time=2.0)\n        self.play(Write(question3), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 11 (50.0s - 55.0s, duration 5.0s)\n        values3 = MathTex(\"a = 24, \\\\quad d = -3, \\\\quad S_n = 78\", font_size=26).shift(DOWN*0.2)\n        setup = MathTex(\"78 = \\\\frac{n}{2}[2(24) + (n-1)(-3)]\", font_size=24).next_to(values3, DOWN, buff=0.4)\n        self.play(Write(values3), run_time=2.0)\n        self.play(Write(setup), run_time=2.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 12 (55.0s - 60.0s, duration 5.0s)\n        quad = MathTex(\"n^2 - 17n + 52 = 0\", font_size=28).shift(DOWN*1.8)\n        factored = MathTex(\"(n - 13)(n - 4) = 0\", font_size=28).next_to(quad, DOWN, buff=0.4)\n        solutions = MathTex(\"n = 4 \\\\text{ or } n = 13\", font_size=28, color=GOLD).next_to(factored, DOWN, buff=0.4)\n        self.play(Write(quad), run_time=1.5)\n        self.play(Write(factored), run_time=1.5)\n        self.play(Write(solutions), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 13 (60.0s - 65.0s, duration 5.0s)\n        self.play(FadeOut(ap3), FadeOut(question3), FadeOut(values3), FadeOut(setup), FadeOut(quad), FadeOut(factored), FadeOut(solutions), run_time=1.0)\n        ex4_title = Text(\"Sum: 1 + 2 + 3 + ... + 1000\", font_size=32, color=BLUE).to_edge(UP)\n        sum_formula = MathTex(\"S = \\\\frac{1000}{2}(1 + 1000)\", font_size=28).shift(UP*0.5)\n        answer4 = MathTex(\"S = 500500\", font_size=32, color=GOLD).next_to(sum_formula, DOWN, buff=0.5)\n        self.play(Transform(ex1_title, ex4_title), run_time=1.0)\n        self.play(Write(sum_formula), run_time=2.0)\n        self.play(Write(answer4), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 14 (65.0s - 70.0s, duration 5.0s)\n        general = Text(\"General Formula for 1+2+...+n:\", font_size=28).shift(DOWN*0.8)\n        gen_formula = MathTex(\"S = \\\\frac{n(n+1)}{2}\", font_size=32, color=GREEN).next_to(general, DOWN, buff=0.5)\n        self.play(Write(general), run_time=2.0)\n        self.play(Write(gen_formula), run_time=2.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 15 (70.0s - 75.0s, duration 5.0s)\n        self.play(FadeOut(sum_formula), FadeOut(answer4), FadeOut(general), FadeOut(gen_formula), run_time=1.0)\n        ex5_title = Text(\"Example: a_n = 3 + 2n\", font_size=32, color=BLUE).to_edge(UP)\n        find5 = Text(\"Find sum of first 24 terms\", font_size=28).shift(UP*0.8)\n        self.play(Transform(ex1_title, ex5_title), run_time=1.0)\n        self.play(Write(find5), run_time=2.0)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 16 (75.0s - 80.0s, duration 5.0s)\n        terms = MathTex(\"a_1 = 5, \\\\quad a_2 = 7, \\\\quad a_3 = 9\", font_size=26).shift(UP*0.2)\n        ap_check = MathTex(\"a = 5, \\\\quad d = 2\", font_size=26, color=YELLOW).next_to(terms, DOWN, buff=0.4)\n        calc5 = MathTex(\"S_{24} = \\\\frac{24}{2}[2(5) + 23(2)] = 672\", font_size=26).next_to(ap_check, DOWN, buff=0.5)\n        self.play(Write(terms), run_time=1.5)\n        self.play(Write(ap_check), run_time=1.5)\n        self.play(Write(calc5), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 17 (80.0s - 85.0s, duration 5.0s)\n        self.play(FadeOut(find5), FadeOut(terms), FadeOut(ap_check), FadeOut(calc5), run_time=1.0)\n        ex6_title = Text(\"TV Production Problem\", font_size=32, color=BLUE).to_edge(UP)\n        given6 = MathTex(\"a_3 = 600, \\\\quad a_7 = 700\", font_size=28).shift(UP*0.5)\n        self.play(Transform(ex1_title, ex6_title), run_time=1.0)\n        self.play(Write(given6), run_time=2.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 18 (85.0s - 90.0s, duration 5.0s)\n        eq_sys1 = MathTex(\"a + 2d = 600\", font_size=26).shift(DOWN*0.2)\n        eq_sys2 = MathTex(\"a + 6d = 700\", font_size=26).next_to(eq_sys1, DOWN, buff=0.3)\n        solve_d = MathTex(\"d = 25, \\\\quad a = 550\", font_size=28, color=YELLOW).next_to(eq_sys2, DOWN, buff=0.5)\n        self.play(Write(eq_sys1), run_time=1.5)\n        self.play(Write(eq_sys2), run_time=1.5)\n        self.play(Write(solve_d), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 19 (90.0s - 95.0s, duration 5.0s)\n        a10_calc = MathTex(\"a_{10} = 550 + 9(25) = 775\", font_size=28).shift(DOWN*2.0)\n        self.play(Write(a10_calc), run_time=2.5)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 20 (95.0s - 100.0s, duration 5.0s)\n        s7_calc = MathTex(\"S_7 = \\\\frac{7}{2}[2(550) + 6(25)] = 4375\", font_size=26).next_to(a10_calc, DOWN, buff=0.5)\n        conclusion = Text(\"Formulas are powerful!\", font_size=28, color=GREEN).next_to(s7_calc, DOWN, buff=0.6)\n        self.play(Write(s7_calc), run_time=2.0)\n        self.play(Write(conclusion), run_time=2.5)\n        self.wait(0.5)\n        # Hard Sync WARNING: Animation exceeds audio by 5.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      },
      "content": "## Sum of First n Terms of an AP\n\n$$S = \\frac{n}{2}[2a + (n - 1)d] \\text{ [First term - } a, \\text{ Common difference - } d]$$\n\n$$S = \\frac{n}{2}[a + l] \\text{ [First term - } a, \\text{ last term - } l]$$\n\nExample 11: Find the sum of the first 22 terms of the AP: 8, 3, -2, ...\n\nSolution:\n\nHere  $a = 8$ ,  $d = -5$ ,  $n = 22$ .\n\n$$\\begin{aligned}S &= \\frac{n}{2}[2a + (n - 1)d] \\\\ S &= \\frac{22}{2}[2 \\times 8 + (22 - 1)(-5)] \\\\ S &= 11[16 + 21(-5)] \\\\ S &= 11[16 - 105] \\\\ S &= 11 \\times -89 = -979\\end{aligned}$$\n\nExample 12: If the sum of the first 14 terms of an AP is 1050 and its first term is 10, find the 20th term.\n\nSolution: Here,\n\n$$S_{14} = 1050, n = 14, a = 10$$\n\n$$\\begin{aligned}S &= \\frac{n}{2}[2a + (n-1)d] \\\\1050 &= \\frac{14}{2}[2 \\times 10 + (14-1)d] \\\\1050 &= 7[20 + 13d] \\\\1050 &= 140 + 91d \\\\91d &= 1050 - 140 \\\\91d &= 910 \\\\d &= \\frac{910}{91} = 10 \\\\a_n &= a + (n-1)d \\\\a_{20} &= 10 + (20-1)10 \\\\a_{20} &= 10 + 19 \\times 10 \\\\a_{20} &= 10 + 190 \\\\a_{20} &= 200\\end{aligned}$$\n\nExample 13 : How many terms of the AP: 24, 21, 18, ... must be taken so that their sum is 78 ?\n\nSolution:  $a = 24, d = 21 - 24 = -3, S_n = 78$ , We have to find 'n'\n\n$$\\begin{aligned}S &= \\frac{n}{2}[2a + (n-1)d] \\\\78 &= \\frac{n}{2}[2 \\times 24 + (n-1)(-3)] \\\\78 &= \\frac{n}{2}[48 - 3n + 3] \\\\156 &= n[48 - 3n + 3] = 51n - 3n^2 \\\\52 &= 17n - n^2 \\\\n^2 - 17n + 52 &= 0 \\\\n^2 - 13n - 4n + 52 &= 0 \\\\(n-13)(n-4) &= 0 \\\\n &= 13 \\text{ OR } n = 4\\end{aligned}$$\n\nExample 14 : Find the sum of:\n\n(i) the first **1000** positive integers  \n(ii) the first **n** positive integers\n\nSolution:\n\n(i) Let  $S = 1 + 2 + 3 + \\dots + 1000$\n\n$$\\begin{aligned}S &= \\frac{n}{2}[2a + (n-1)d] \\\\S &= 500[2 + 999] \\\\S &= 500[1001] \\\\S &= 500500\\end{aligned}$$\n\n(ii) Let  $S = 1 + 2 + 3 + \\dots + n$\n\n$$\\begin{aligned}S &= \\frac{n}{2}[2a + (n-1)d] \\\\S &= \\frac{n}{2}[2 \\times 1 + (n-1)1]\\end{aligned}$$\n\n$$S = \\frac{n}{2}[2 + n - 1]$$\n\n$$S = \\frac{n}{2}[n + 1]$$\n\nExample 15: Find the sum of first 24 terms of the list of numbers whose **n**th term is given by  $a_n = 3 + 2n$ .\n\nSolution:\n\n$$a_n = 3 + 2n$$\n\n$$a_1 = 3 + 2 \\times 1 = 3 + 2 = 5$$\n\n$$a_2 = 3 + 2 \\times 2 = 3 + 4 = 7$$\n\n$$a_3 = 3 + 2 \\times 3 = 3 + 6 = 9$$\n\nThere for AP is : 5, 7, 9, ---\n\n$$a = 5, d = 2, n = 24$$\n\n$$S = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S = \\frac{24}{2}[2 \\times 5 + (24 - 1)2]$$\n\n$$S = 12[10 + 23 \\times 2]$$\n\n$$S = 12[10 + 46]$$\n\n$$S = 12 \\times 56$$\n\n$$S = 672$$\n\nExample 16: A manufacturer of TV sets produced 600 sets in the third year and 700 sets in the seventh year. Assuming that the production increases uniformly by a fixed number every year, find\n\n: (i) the production in the 1st year\n\n(ii) the production in the 10th year\n\n(iii) the total production in first 7 years\n\nSolution:i) Since the production increases uniformly by a fixed number every year, the number of TV sets manufactured in 1st, 2nd, 3rd . . . years will form an AP.\n\nLet us denote the number of TV sets manufactured in the  $n$ th year by  $a_n$\n\n$$a_3 = 600, a_7 = 700,$$\n\n$$a + 2d = 600$$\n\n$$a + 6d = 700$$\n\nBy solving the equation we get,\n\n$$d = 25 \\text{ and } a = 550$$\n\nTherefore, production\n\n(i) of TV sets in the first year is = 550\n\n(ii) Production of TV sets in the 10th year is :  $a_{10} = a + 9d$\n\n$$a_{10} = 550 + 9 \\times 25 = 550 + 225 = 775$$\n\n(iii) The total production of TV sets in first 7 years is\n\n$$S = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S = \\frac{7}{2}[2 \\times 550 + (7 - 1)25]$$\n\n$$S = \\frac{7}{2}[1100 + 6 \\times 25]$$\n\n$$S = \\frac{7}{2}[1100 + 150]$$\n\n$$\\begin{aligned}S &= \\frac{7}{2}[1250] \\\\S &= 7 \\times 625 \\\\S &= 4375\\end{aligned}$$\n\n"
    },
    {
      "section_id": 11,
      "section_type": "example",
      "title": "Exercise 5.3: Finding the Sum of APs",
      "renderer": "manim",
      "narration": {
        "full_text": "Welcome back! Today, we'll tackle some problems from Exercise 5.3. First up, we need to find the sum of a few Arithmetic Progressions. Imagine you're saving for Diwali. You start with a small amount and add a fixed amount each day. How much would you have in total after a set number of days? That's exactly what we are doing here! Let's start with the first problem: 2, 7, 12 and so on for 10 terms. We'll use our sum formula. Watch how it's done. Here, 'a' is 2, 'd' is 5, and 'n' is 10. We substitute these values into the formula S_n equals n by 2 into 2a plus n minus 1 into d. The calculation simplifies to 5 times 49, giving us a sum of 245. Now for the second one, which includes negative numbers. Don't worry, the process is exactly the same! The AP is -37, -33, -29, for 12 terms. 'a' is -37, 'd' is 4, and 'n' is 12. Plugging these into our trusty formula, we get 6 times -74 plus 44. This gives us 6 times -30, which equals -180. Next, we have a series with decimals: 0.6, 1.7, 2.8 and so on for 100 terms. It might look a bit tricky, but the steps don't change at all. Here, a is 0.6, d is 1.1, and n is 100. Let's see the calculation. After substituting the values, we have 50 multiplied by 1.2 plus 108.9. The final sum is a large number, 5505. Finally, let's look at an AP with fractions. It's just like dividing a chapati among friends; the maths is the same! The series is 1 by 15, 1 by 12, 1 by 10, for 11 terms. Here, the first term 'a' is 1 by 15, and the common difference 'd' is 1 by 60. Let's calculate the sum for 11 terms. We substitute the values, find a common denominator for the fractions inside the bracket, and simplify. The final answer comes out to be 33 by 20.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Welcome back! Today, we'll tackle some problems from Exercise 5.3. First up, we need to find the sum of a few Arithmetic Progressions. Imagine you're saving for Diwali. You start with a small amount and add a fixed amount each day. How much would you have in total after a set number of days? That's exactly what we are doing here!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Let's start with the first problem: 2, 7, 12 and so on for 10 terms. We'll use our sum formula. Watch how it's done.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Here, 'a' is 2, 'd' is 5, and 'n' is 10. We substitute these values into the formula S_n equals n by 2 into 2a plus n minus 1 into d. The calculation simplifies to 5 times 49, giving us a sum of 245.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Now for the second one, which includes negative numbers. Don't worry, the process is exactly the same!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "The AP is -37, -33, -29, for 12 terms. 'a' is -37, 'd' is 4, and 'n' is 12. Plugging these into our trusty formula, we get 6 times -74 plus 44. This gives us 6 times -30, which equals -180.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "Next, we have a series with decimals: 0.6, 1.7, 2.8 and so on for 100 terms. It might look a bit tricky, but the steps don't change at all.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "Here, a is 0.6, d is 1.1, and n is 100. Let's see the calculation. After substituting the values, we have 50 multiplied by 1.2 plus 108.9. The final sum is a large number, 5505.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "Finally, let's look at an AP with fractions. It's just like dividing a chapati among friends; the maths is the same!",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_9",
            "text": "The series is 1 by 15, 1 by 12, 1 by 10, for 11 terms. Here, the first term 'a' is 1 by 15, and the common difference 'd' is 1 by 60. Let's calculate the sum for 11 terms. We substitute the values, find a common denominator for the fractions inside the bracket, and simplify. The final answer comes out to be 33 by 20.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "## Exercise 5.3\n\n1. Find the",
            "end_phrase": "sum of the following APs:"
          },
          "display_text": "## Exercise 5.3\n\n1. Find the sum of the following APs:",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "i) 2,7,12... to 10 terms\n\n$$a",
            "end_phrase": "S_{10} = 245$$"
          },
          "display_text": "i) 2,7,12... to 10 terms\n\n$$a = 2, d = a_2 - a_1 = 7 - 2 = 5, n = 10$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{10} = 5 \\times 49 = 245$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_4",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "ii) -37, -33, -29 ... to",
            "end_phrase": "$$S_{12} = 6(-30) = -180$$"
          },
          "display_text": "ii) -37, -33, -29 ... to 12 terms\n\n$$a = -37; d = 4; n = 12$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{12} = 6(-30) = -180$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "iii) 0,6,1,7,2,5 ... to 100",
            "end_phrase": "$$S_{100} = 5505$$"
          },
          "display_text": "iii) 0.6, 1.7, 2.8 ... to 100 terms\n\n$$a = 0.6; d = 1.1; n = 100$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{100} = 5505$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_8",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "iv)  $\\frac{1}{15}, \\frac{1}{12}, \\frac{1}{10}$",
            "end_phrase": "$$S_{11} = \\frac{33}{20}$$"
          },
          "display_text": "iv)  $\\frac{1}{15}, \\frac{1}{12}, \\frac{1}{10}$  to 11 terms\n\n$$a = \\frac{1}{15}; d = \\frac{1}{60}; n = 11$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{11} = \\frac{33}{20}$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "The scene will animate the solutions to the four sub-problems of Question 1. For each sub-problem, the title, e.g., 'i) 2,7,12... to 10 terms', appears. The formula `S_n = n/2[2a + (n-1)d]` is displayed prominently. The values of 'a', 'd', and 'n' are extracted from the problem and glow. These values are then substituted into the formula in a visually engaging way. The calculation proceeds step-by-step, with each simplification animated (e.g., `(10-1)5` becomes `9*5`, then `45`). The final result is revealed and highlighted. Smooth, clean transitions will move from one sub-problem to the next, maintaining the formula on screen as a constant reference. The background is a calm, dark blue, with numbers and formulas in bright white and yellow for clarity.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.3: Finding the Sum of APs\", font_size=36).to_edge(UP)\n        subtitle = Text(\"Saving for Diwali Example\", font_size=28, color=YELLOW).next_to(title, DOWN)\n        self.play(Write(title), run_time=2.0)\n        self.play(FadeIn(subtitle), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(subtitle), run_time=0.5)\n        problem1 = Text(\"i) 2, 7, 12, ... to 10 terms\", font_size=30).next_to(title, DOWN, buff=0.5)\n        formula = MathTex(\"S_n = \\\\frac{n}{2}[2a + (n-1)d]\", font_size=40).shift(UP*0.5)\n        self.play(Write(problem1), run_time=1.5)\n        self.play(Write(formula), run_time=2.0)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        values1 = MathTex(\"a = 2,\\\\quad d = 5,\\\\quad n = 10\", font_size=32).next_to(formula, DOWN, buff=0.5)\n        self.play(Write(values1), run_time=1.5)\n        calc1 = MathTex(\"S_{10} = \\\\frac{10}{2}[2(2) + (10-1)5]\", font_size=32).next_to(values1, DOWN, buff=0.4)\n        self.play(Write(calc1), run_time=1.5)\n        result1 = MathTex(\"= 5 \\\\times 49 = 245\", font_size=32, color=YELLOW).next_to(calc1, DOWN, buff=0.3)\n        self.play(Write(result1), run_time=1.0)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(problem1, values1, calc1, result1), run_time=1.0)\n        problem2 = Text(\"ii) -37, -33, -29, ... to 12 terms\", font_size=30).next_to(title, DOWN, buff=0.5)\n        note = Text(\"(Negative numbers - same process!)\", font_size=24, color=GREEN).next_to(problem2, DOWN, buff=0.3)\n        self.play(Write(problem2), run_time=1.5)\n        self.play(FadeIn(note), run_time=1.0)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(note), run_time=0.5)\n        values2 = MathTex(\"a = -37,\\\\quad d = 4,\\\\quad n = 12\", font_size=32).next_to(formula, DOWN, buff=0.5)\n        self.play(Write(values2), run_time=1.5)\n        calc2 = MathTex(\"S_{12} = 6[-74 + 44]\", font_size=32).next_to(values2, DOWN, buff=0.4)\n        self.play(Write(calc2), run_time=1.5)\n        result2 = MathTex(\"= 6 \\\\times (-30) = -180\", font_size=32, color=YELLOW).next_to(calc2, DOWN, buff=0.3)\n        self.play(Write(result2), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        self.play(FadeOut(problem2, values2, calc2, result2), run_time=1.0)\n        problem3 = Text(\"iii) 0.6, 1.7, 2.8, ... to 100 terms\", font_size=30).next_to(title, DOWN, buff=0.5)\n        note2 = Text(\"(Decimals - same steps!)\", font_size=24, color=GREEN).next_to(problem3, DOWN, buff=0.3)\n        self.play(Write(problem3), run_time=1.5)\n        self.play(FadeIn(note2), run_time=1.0)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(note2), run_time=0.5)\n        values3 = MathTex(\"a = 0.6,\\\\quad d = 1.1,\\\\quad n = 100\", font_size=32).next_to(formula, DOWN, buff=0.5)\n        self.play(Write(values3), run_time=1.5)\n        calc3 = MathTex(\"S_{100} = 50[1.2 + 108.9]\", font_size=32).next_to(values3, DOWN, buff=0.4)\n        self.play(Write(calc3), run_time=1.5)\n        result3 = MathTex(\"= 50 \\\\times 110.1 = 5505\", font_size=32, color=YELLOW).next_to(calc3, DOWN, buff=0.3)\n        self.play(Write(result3), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        self.play(FadeOut(problem3, values3, calc3, result3), run_time=1.0)\n        problem4 = Text(\"iv) 1/15, 1/12, 1/10, ... to 11 terms\", font_size=30).next_to(title, DOWN, buff=0.5)\n        note3 = Text(\"(Fractions - like dividing chapati!)\", font_size=24, color=GREEN).next_to(problem4, DOWN, buff=0.3)\n        self.play(Write(problem4), run_time=1.5)\n        self.play(FadeIn(note3), run_time=1.0)\n        self.wait(2.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 9 (40.0s - 45.0s, duration 5.0s)\n        self.play(FadeOut(note3), run_time=0.5)\n        values4 = MathTex(\"a = \\\\frac{1}{15},\\\\quad d = \\\\frac{1}{60},\\\\quad n = 11\", font_size=30).next_to(formula, DOWN, buff=0.5)\n        self.play(Write(values4), run_time=1.5)\n        calc4 = MathTex(\"S_{11} = \\\\frac{11}{2}[\\\\frac{2}{15} + \\\\frac{10}{60}]\", font_size=28).next_to(values4, DOWN, buff=0.4)\n        self.play(Write(calc4), run_time=1.5)\n        result4 = MathTex(\"= \\\\frac{33}{20}\", font_size=32, color=YELLOW).next_to(calc4, DOWN, buff=0.3)\n        self.play(Write(result4), run_time=1.0)\n        self.wait(0.5)\n        # Hard Sync WARNING: Animation exceeds audio by 5.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      },
      "content": "## Exercise 5.3\n\n1. Find the sum of the following APs:\n\ni) 2,7,12 ... to 10 terms ii) -37, -33, -29 ... to 12 terms iii) 0,6,1,7,2,5 ... to 100 terms iv)  $\\frac{1}{15}, \\frac{1}{12}, \\frac{1}{10}$  ... to 11 terms\n\ni) 2,7,12... to 10 terms\n\n$$a = 2, d = a_2 - a_1 = 7 - 2 = 5, n = 10$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{10} = \\frac{10}{2}[2(2) + (10 - 1) \\times 5]$$\n\n$$S_{10} = 5[4 + (9 \\times 5)]$$\n\n$$S_{10} = 5[4 + 45]$$\n\n$$S_{10} = 5 \\times 49 = 245$$\n\n$$S_{10} = 245$$\n\nii) -37, -33, -29 ... to 12 terms\n\n$$a = -37; d = 4; n = 12$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{12} = \\frac{12}{2}[2(-37) + (12 - 1) \\times 4]$$\n\n$$S_{12} = 6[-74 + 11 \\times 4]$$\n\n$$S_{12} = 6[-74 + 44]$$\n\n$$S_{12} = 6(-30) = -180$$\n\niii) 0,6,1,7,2,5 ... to 100 terms\n\n$$a = 0.6; d = 1.1; n = 100$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{100} = \\frac{100}{2}[1. + (99) \\times 1.1]$$\n\n$$S_{100} = 50[1.2 + 108.9]$$\n\n$$S_{100} = 50[110.1]2$$\n\n$$S_{100} = 5505$$\n\niv)  $\\frac{1}{15}, \\frac{1}{12}, \\frac{1}{10}$  to 11 terms\n\n$$a = \\frac{1}{15}; d = \\frac{1}{12} - \\frac{1}{15} = \\frac{5-4}{60} = \\frac{1}{60}; n = 11$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{11} = \\frac{11}{2}\\left[2 \\times \\frac{1}{15} + (11 - 1) \\times \\frac{1}{60}\\right]$$\n\n$$S_{11} = \\frac{11}{2}\\left[\\frac{2}{15} + \\frac{10}{60}\\right]$$\n\n$$S_{11} = \\frac{11}{2}\\left[\\frac{8+10}{60}\\right]$$\n\n$$S_{11} = \\frac{11}{2}\\left[\\frac{18}{60}\\right]$$\n\n$$S_{11} = \\frac{11}{2} \\left[ \\frac{3}{10} \\right]$$\n$$S_{11} = \\frac{33}{20}$$\n\n2. Find the sums given below :\n\n$$\\text{i) } 7 + 10\\frac{1}{2} + 14 + \\dots + 84 \\quad \\text{ii) } 34 + 32 + 30 + \\dots + 10 \\quad \\text{iii) } -5 + (-8) + (-11) + \\dots + (-230)$$\n\n$$\\text{i) } 7 + 10\\frac{1}{2} + 14 + \\dots + 84$$\n\n$$a = 7; l = 84; d = \\frac{7}{2}$$\n\n$$l = a + (n - 1)d$$\n\n$$84 = 7 + (n - 1) \\times \\frac{7}{2}$$\n\n$$77 = (n - 1) \\times \\frac{7}{2}$$\n\n$$154 = 7n - 7$$\n\n$$7n = 161$$\n\n$$\\mathbf{n = 23}$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$S_{23} = \\frac{23}{2}(7 + 84)$$\n\n$$= \\frac{23}{2} \\times 91 = \\frac{2093}{2}$$\n\n$$= 1046\\frac{1}{2}$$\n\n$$\\text{ii) } 34 + 32 + 30 + \\dots + 10$$\n\n$$a = 34, d = -2, l = 10$$\n\n$$l = a + (n - 1)d$$\n\n$$10 = 34 + (n - 1)(-2)$$\n\n$$-24 = (n - 1)(-2)$$\n\n$$12 = n - 1$$\n\n$$\\mathbf{n = 13}$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$S_{13} = \\frac{13}{2}(34 + 10)$$\n\n$$S_{13} = \\frac{13}{2} \\times 44 = 13 \\times 22$$\n\n$$S_{13} = 286$$\n\n$$\\text{iii) } -5 + (-8) + (-11) + \\dots + (-230)$$\n\n$$a = -5, l = -230,$$\n\n$$d = a_2 - a_1 = -3$$\n\n$$l = a + (n - 1)d$$\n\n$$-230 = -5 + (n - 1)(-3)$$\n\n$$-225 = (n - 1)(-3)$$\n\n$$(n - 1) = 75$$\n\n$$\\mathbf{n = 76}$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$\\begin{aligned}S_{76} &= \\frac{76}{2} [(-5) + (-230)] \\\\S_{76} &= 38(-235) \\\\S_{76} &= -8930\\end{aligned}$$\n\n3. In an AP:\n\ni) Given  $a = 5$ ,  $d = 3$ ,  $a_n = 50$  find  $n$  and  $S_n$\n\nii) Given  $a = 7$ ,  $a_{13} = 35$  find  $d$  and  $S_{13}$\n\niii) Given  $a_{12} = 37$ ,  $d = 3$  find  $E$  and  $S_{12}$\n\niv) Given  $a_3 = 15$ ,  $S_{10} = 125$  find  $d$  and  $a_{10}$\n\nv) Given  $d = 5$ ,  $S_9 = 75$  find  $a$  and  $a_9$\n\nvi) Given  $a = 2$ ,  $d = 8$ ,  $S_n = 90$  find  $n$  and  $a_n$\n\nvii) Given  $a = 8$ ,  $a_n = 62$ ,  $S_n = 210$  find  $n$  and  $d$\n\nviii) Given  $a_n = 4$ ,  $d = 2$ ,  $S_n = -14$  find  $n$  and  $a$\n\nix) Given  $a = 3$ ,  $n = 8$ ,  $S = 192$  find  $d$\n\nx) Given  $l = 28$ ,  $S = 144$  and there are 9 terms. Find the value of  $a$\n\nSolution:\n\ni) Given  $a = 5$ ,  $d = 3$ ,  $a_n = 50$  find  $n$  and  $S_n$\n\n$$a = 5, d = 3, a_n = 50$$\n\n$$a_n = a + (n - 1)d,$$\n\n$$\\Rightarrow 50 = 5 + (n - 1) \\times 3$$\n\n$$\\Rightarrow 3(n - 1) = 45$$\n\n$$\\Rightarrow n - 1 = 15$$\n\n$$n = 16$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$S_{16} = \\frac{16}{2}(5 + 50) = 440$$\n\n$$S_{16} = 8(55)$$\n\n$$S_{16} = 440$$\n\nii) Given  $a = 7$ ,  $a_{13} = 35$  find  $d$  and  $S_{13}$\n\n$$a = 7, a_{13} = 35$$\n\n$$a_n = a + (n - 1)d,$$\n\n$$\\Rightarrow 35 = 7 + (13 - 1)d$$\n\n$$\\Rightarrow 12d = 28$$\n\n$$\\Rightarrow d = 28/12 = 2.33$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$S_{13} = \\frac{13}{2}(7 + 35)$$\n\n$$S_{13} = \\frac{13}{2}(42) = 13 \\times 21$$\n\n$$S_{13} = 273$$\n\niii) Given  $a_{12} = 37$ ,  $d = 3$  find  $a$  and  $S_{12}$\n\n$$a_{12} = 37, d = 3$$\n\n$$a_n = a + (n - 1)d,$$\n\n$$\\Rightarrow a_{12} = a + (12 - 1)3$$\n\n$$\\Rightarrow 37 = a + 33$$\n\n$$\\Rightarrow a = 4$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$S_{12} = \\frac{12}{2}(4 + 37)$$\n\n$$S_{12} = 6(41)$$\n\n$$S_{12} = 246$$\n\niv) Given  $a_3 = 15$ ,  $S_{10} = 125$  find  $d$  and  $a_{10}$\n\n$$a_3 = 15, S_{10} = 125$$\n\n$$a_n = a + (n - 1)d,$$\n\n$$a_3 = a + (3 - 1)d$$\n\n$$15 = a + 2d$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{10} = \\frac{10}{2}[2a + (10 - 1)d]$$\n\n$$125 = 5(2a + 9d)$$\n\n$$25 = 2a + 9d$$\n\n$$(i) \\times 2$$\n\n$$30 = 2a + 4d$$\n\n(iii)\n\n$$(iii) - (ii)$$\n\n$$-5 = 5d$$\n\n$$d = -1$$\n\nFrom equation (i),\n\n$$15 = a + 2(-1) = a - 2$$\n\n$$a = 17$$\n\n$$a_{10} = a + (10 - 1)d$$\n\n$$a_{10} = 17 + (9)(-1)$$\n\n$$a_{10} = 17 - 9$$\n\n$$a_{10} = 8$$\n\nv) Given  $d = 5$ ,  $S_9 = 75$  find  $a$  and  $a_9$\n\n$$d = 5, S_9 = 75$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$75 = \\frac{9}{2}[2a + (9 - 1)5]$$\n\n$$75 = \\frac{9}{2}(2a + 40) = 9(a + 20)$$\n\n$$75 = 9a + 180 \\Rightarrow 9a = 75 - 180$$\n\n$$9a = \\frac{-105}{3} \\Rightarrow a = \\frac{-35}{3}$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_9 = a + (9 - 1)5 = \\frac{-35}{3} + 8(5)$$\n\n$$= \\frac{-35}{3} + 40 = \\frac{-35 + 120}{3} = \\frac{85}{3}$$\n\nvi) Given  $a = 2$ ,  $d = 8$ ,  $S_n = 90$  find  $n$  and  $a_n$\n\n$$a = 2, d = 8, S_n = 90$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$90 = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$\\Rightarrow 180 = n(4 + 8n - 8)$$\n\n$$\\Rightarrow 180 = n(8n - 4)$$\n\n$$\\Rightarrow 180 = 8n^2 - 4n$$\n\n$$\\Rightarrow 8n^2 - 4n - 180 = 0$$\n\n$$\\Rightarrow 2n^2 - n - 45 = 0$$\n\n$$\\Rightarrow 2n^2 - 10n + 9n - 45 = 0$$\n\n$$\\Rightarrow 2n(n-5) + 9(n-5) = 0$$\n\n$$\\Rightarrow (2n-9)(2n+9) = 0$$\n\n$$n = 5 \\text{ (Positive number)}$$\n\n$$\\text{There for } a_5 = 8 + 5 \\times 4 = 34$$\n\nvii) Given **a** = 8, **an** = 62, **Sn** = 210 find **n** and **d**\n\n$$a = 8, a_n = 62, S_n = 210$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$210 = \\frac{n}{2}(8 + 62)$$\n\n$$\\Rightarrow 35n = 210$$\n\n$$\\Rightarrow n = \\frac{210}{35} = 6$$\n\n$$a_n = a + (n-1)d$$\n\n$$62 = 8 + 5d$$\n\n$$\\Rightarrow 5d = 62 - 8 = 54$$\n\n$$\\Rightarrow d = \\frac{54}{5}$$\n\n$$\\Rightarrow d = 10.8$$\n\nviii) Given  $a_n = 4$ ,  $d = 2$ ,  $S_n = -14$  find  $n$  and  $a$\n\n$$a_n = 4, d = 2, S_n = -14$$\n\n$$a_n = a + (n-1)d$$\n\n$$4 = a + (n-1)2$$\n\n$$4 = a + 2n - 2$$\n\n$$a + 2n = 6$$\n\n$$a = 6 - 2n$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$-14 = \\frac{n}{2}(a + 4)$$\n\n$$-28 = n(a + 4)$$\n\n$$-28 = n(6 - 2n + 4) \\text{ From (i)}$$\n\n$$-28 = n(-2n + 10)$$\n\n$$-28 = -2n^2 + 10n$$\n\n$$2n^2 - 10n - 28 = 0$$\n\n$$n^2 - 5n - 14 = 0$$\n\n$$n^2 - 7n + 2n - 14 = 0$$\n\n$$n(n-7) + 2(n-7) = 0$$\n\n$$(n-7)(n+2) = 0$$\n\n$$n - 7 = 0 \\text{ or } n + 2 = 0$$\n\n$$n = 7 \\text{ or } n = -2$$\n\nFrom equation (i),\n\n$$a = 6 - 2n$$\n\n$$a = 6 - 2(7)$$\n\n$$a = 6 - 14$$\n\n$$a = -8$$\n\nix) Given  $a = 3$ ,  $n = 8$ ,  $S = 192$  find  $d$\n\n$$a = 3, n = 8, S = 192$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$192 = \\frac{8}{2}[2 \\times 3 + (8-1)d]$$\n\n$$192 = 4[6 + 7d]$$\n\n$$48 = 6 + 7d$$\n\n$$42 = 7d$$\n\n$$d = 6$$\n\nx) Given  $l = 28$ ,  $S = 144$  and there are 9 terms. Find the value of  $a$\n\n$$l = 28, S = 144, n = 9$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$144 = \\frac{9}{2}(a + 28)$$\n\n$$(16) \\times (2) = a + 28$$\n\n$$32 = a + 28$$\n\n$$a = 4$$\n\n4. How many terms of the AP: 9, 17, 25, ... must be taken to give a sum of 36 ?\n\n$$a = 9; d = a_2 - a_1 = 17 - 9 = 8$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$636 = \\frac{n}{2}[2 \\times a + (8-1) \\times 8]$$\n\n$$636 = \\frac{n}{2}[18 + (n-1) \\times 8]$$\n\n$$636 = n[9 + 4n - 4]$$\n\n$$636 = n(4n + 5)$$\n\n$$4n^2 + 5n - 636 = 0$$\n\n$$4n^2 + 53n - 48n - 636 = 0$$\n\n$$n(4n + 53) - 12(4n + 53) = 0$$\n\n$$(4n + 53)(n - 12) = 0$$\n\n$$4n + 53 = 0 \\text{ or } n - 12 = 0$$\n\n$$n = (-53/4) \\text{ or } n = 12$$\n\n$$\\Rightarrow n = 12$$\n\n5. The first term of an AP is 5, the last term is 45 and the sum is 400. Find the number of terms and the common difference.\n\n$$a = 5, l = 45, S_n = 400$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$400 = \\frac{n}{2}(5 + 45)$$\n\n$$400 = \\frac{n}{2}(50)$$\n\n$$25n = 400$$\n\n$$n = 16$$\n\n$$l = a + (n-1)d$$\n\n$$45 = 5 + (16 - 1)d$$\n\n$$40 = 15d$$\n\n$$d = \\frac{40}{15}$$\n\n$$d = \\frac{8}{3}$$\n\n6. The first and the last terms of an AP are 17 and 350 respectively. If the common difference is 9, how many terms are there and what is their sum?\n\n$$a = 17, l = 350, d = 9$$\n\n$$l = a + (n - 1)d$$\n\n$$350 = 17 + (n - 1)9$$\n\n$$333 = (n - 1)9$$\n\n$$(n - 1) = 37 \\Rightarrow n = 38$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$S_{38} = \\frac{38}{2}(17 + 350)$$\n\n$$S_{38} = 19 \\times 367$$\n\n$$S_{38} = 6973$$\n\n7. Find the sum of first 22 terms of an AP in which **d = 7** and 22nd term is 149.\n\n$$d = 7, a_{22} = 149, S_{22} = ?$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_{22} = a + (22 - 1)d$$\n\n$$149 = a + 21 \\times 7$$\n\n$$149 = a + 147$$\n\n$$a = 2$$\n\n$$S_n = \\frac{n}{2}(a + a_n)$$\n\n$$S_{22} = \\frac{22}{2}(2 + 149)$$\n\n$$S_{22} = 11 \\times 151$$\n\n$$S_{22} = 1661$$\n\n8. Find the sum of first 51 terms of an AP whose second and third terms are 14 and 18 respectively.\n\n$$a_2 = 14, a_3 = 18, d = 4$$\n\n$$a_2 = a + d$$\n\n$$14 = a + 4$$\n\n$$\\Rightarrow a = 10$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{51} = \\frac{51}{2}[2 \\times 10 + (51 - 1)4]$$\n\n$$= \\frac{51}{2}[20 + (50 \\times 4)]$$\n\n$$= \\frac{51}{2}[20 + 200] = \\frac{51}{2}[220]$$\n\n$$= 51 \\times 110$$\n\n$$= 5610$$\n\n9. If the sum of first 7 terms of an AP is 49 and that of 17 terms is 289, find the sum of first **n** terms.\n\n$$S_7 = 49, S_{17} = 289$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$S_7 = \\frac{7}{2}[2a + (7-1)d]$$\n\n$$S_7 = \\frac{7}{2}[2a + 6d]$$\n\n$$49 = \\frac{7}{2}[2a + 6d]$$\n\n$$7 = (a + 3d)$$\n\n$$a + 3d = 7$$\n\nSimilarly,\n\n$$S_{17} = \\frac{17}{2}[2a + (17-1)d]$$\n\n$$289 = \\frac{17}{2}(2a + 16d)$$\n\n$$17 = (a + 8d)$$\n\n$$a + 8d = 17$$\n\nSubtract equation (ii) from (i)\n\n$$5d = 10$$\n\n$$\\Rightarrow d = 2$$\n\nFrom equation (i)\n\n$$a + 3(2) = 7$$\n\n$$a + 6 = 7$$\n\n$$a = 1$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$S_n = \\frac{n}{2}[2(1) + (n-1) \\times 2]$$\n\n$$S_n = \\frac{n}{2}(2 + 2n - 2)$$\n\n$$S_n = \\frac{n}{2}(2n)$$\n\n$$S_n = n^2$$\n\n10. Show that  $a_1, a_2, a_3 \\dots a_n$  form an AP where  $a_n$  is defined as below\n\n(i)  $a_n = 3 + 4n$  (ii)  $a_n = 9 - 5n$  Also, find the sum of the first 15 terms in each case.\n\n(i)  $a_n = 3 + 4n$\n\n$$a_1 = 3 + 4(1) = 7$$\n\n$$a_2 = 11; a_3 = 15; a_4 = 19$$\n\n$$\\Rightarrow a_2 - a_1 = 11 - 7 = 4$$\n\n$$a_3 - a_2 = 15 - 11 = 4; a_4 - a_3 = 19 - 15 = 4$$\n\nSo, the given sequence forms an AP with  $a = 7$  and  $d = 4$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$S_{15} = \\frac{15}{2}[2(7) + (15-1)4]$$\n\n$$= \\frac{15}{2}[(14) + 56]$$\n\n$$= \\frac{15}{2}(70)$$\n\n$$= 15 \\times 35$$\n\n$$= 525$$\n\n$$(ii) a_n = 9 - 5n$$\n\n$$a_1 = 9 - 5 \\times 1 = 9 - 5 = 4$$\n\n$$a_2 = 9 - 5 \\times 2 = 9 - 10 = -1$$\n\n$$\\therefore a_3 = -6, a_4 = -11$$\n\n$$\\Rightarrow a_2 - a_1 = -1 - 4 = -5$$\n\n$$a_3 - a_2 = -6 - (-1) = -5; a_4 - a_3 = -5$$\n\nSo, the given sequence forms an AP with  $a = 4$  and  $d = -5$\n\n$$S_n = \\frac{n}{2} [2a + (n-1)d]$$\n\n$$S_{15} = \\frac{15}{2} [2(4) + (15-1)(-5)]$$\n\n$$S_{15} = \\frac{15}{2} [8 + 14(-5)]$$\n\n$$S_{15} = \\frac{15}{2} (8 - 70)$$\n\n$$S_{15} = \\frac{15}{2} (-62)$$\n\n$$S_{15} = 15(-31)$$\n\n$$S_{15} = -465$$\n\n11. If the sum of the first  $n$  terms of an AP is  $4n - n^2$ , what is the first term (that is  $S_1$ )? What is the sum of first two terms? What is the second term? Similarly, find the 3rd, the 10th and the  $n^{\\text{th}}$  terms.\n\n$$S_n = 4n - n^2$$\n\n$$a = S_1 = 4(1) - (1)^2 = 4 - 1 = 3$$\n\nSum of first two terms\n\n$$S_2 = 4(2) - (2)^2 = 8 - 4 = 4$$\n\n$$a_2 = S_2 - S_1 = 4 - 3 = 1$$\n\n$$d = a_2 - a = 1 - 3 = -2$$\n\n$$n^{\\text{th}} \\text{ term } a_n = a + (n-1)d$$\n\n$$= 3 + (n-1)(-2)$$\n\n$$= 3 - 2n + 2$$\n\n$$= 5 - 2n$$\n\n$$\\text{So, the third term } a_3 = 5 - 2(3)$$\n\n$$= 5 - 6 = -1$$\n\n$$10^{\\text{th}} \\text{ term } a_{10} = 5 - 2(10)$$\n\n$$= 5 - 20$$\n\n$$= -15$$\n\n12. Find the sum of the first 40 positive integers divisible by 6.\n\nThe positive integers divisible by 6 are 6, 12, 18, 24 ...\n\nThis is an AP with  $d = 6$  and  $a = 6$\n\n$$S_{40} = ?$$\n\n$$S_n = \\frac{n}{2} [2a + (n-1)d]$$\n\n$$S_{40} = \\frac{40}{2} [2(6) + (40-1)6]$$\n\n$$= 20[12 + (39)(6)]$$\n\n$$= 20(12 + 234) = 20 \\times 246$$\n\n$$= 4920$$\n\n13. Find the sum of the first 15 multiples of 8.\n\nThe numbers multiples of 8 are\n\n8,16,24,32 ...\n\nThese form an AP with  $d = 8$  and  $a = 8$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$S_{15} = \\frac{15}{2}[2(8) + (15-1)8]$$\n\n$$= \\frac{15}{2}[6 + (14)(8)]$$\n\n$$= \\frac{15}{2}[16 + 112]$$\n\n$$= \\frac{15}{2}(128)$$\n\n$$= 15 \\times 64$$\n\n$$= 960$$\n\n14. Find the sum of the odd numbers between 0 and 50.\n\nThe odd numbers between 0 and 50\n\n1,3,5,7,9 ... 49\n\nThis is an AP with  $a = 1$  and  $d = 2$\n\n$$a = 1, d = 2, l = 49$$\n\n$$l = a + (n-1)d$$\n\n$$49 = 1 + (n-1)2$$\n\n$$48 = 2(n-1)$$\n\n$$n-1 = 24$$\n\n$$n = 25$$\n\n$$S_n = \\frac{n}{2}(a + l)$$\n\n$$\\Rightarrow S_{25} = \\frac{25}{2}(1 + 49)$$\n\n$$S_n = \\frac{25}{2}(50)$$\n\n$$= (25)(25)$$\n\n$$= 625$$\n\n15. A contract on construction job specifies a penalty for delay of completion beyond a certain date as follows: Rs 200 for the first day, Rs 250 for the second day, Rs 300 for the third day, etc., the penalty for each succeeding day being Rs 50 more than for the preceding day. How much money the contractor has to pay as penalty, if he has delayed the work by 30 days?\n\nThis is an AP with common difference 50 and the first term 200 [ $a = 200, d = 50$ ]\n\nThe penalty payable for the delay of 30 days =  $S_{30}$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$\\Rightarrow S_{30} = \\frac{30}{2}[2(200) + (30-1)50]$$\n\n$$\\Rightarrow S_{30} = 15[400 + 1450]$$\n\n$$= 15 (1850)$$\n\n$$= \\text{Rs } 27750$$\n\n16. A sum of Rs 700 is to be used to give seven cash prizes to students of a school for their overall academic performance. If each prize is **Rs 20** less than its preceding prize, find the value of each of the prizes.\n\nLet the first prize =  $a$\n\nThe amount of 2<sup>nd</sup> prize =  $a - 20$\n\nThe amount of 3<sup>rd</sup> prize =  $a - 40$\n\nThis is an AP with  $d = -20$  and  $a = a$\n\n$$d = -20, S_7 = 700$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$\\frac{7}{2}[2a + (7-1)d] = 700$$\n\n$$\\frac{7}{2}[2a + 6d] = 700$$\n\n$$7[a + 3d] = 700$$\n\n$$a + 3d = 100$$\n\n$$a + 3(-20) = 100$$\n\n$$a - 60 = 100$$\n\n$$a = 160$$\n\nSo, the values of prizes Rs 160, Rs 140, Rs 120, Rs 100, Rs 80, Rs 60, and Rs 40.\n\n17. In a school, students thought of planting trees in and around the school to reduce air pollution. It was decided that the number of trees, that each section of each class will plant, will be the same as the class, in which they are studying, e.g., a section of Class I will plant 1 tree, a section of Class II will plant 2 trees and so on till Class XII. There are three sections of each class. How many trees will be planted by the students?\n\nSolution: 1,2,3,4,5,12\n\nThis is an AP with common difference 1 and the first term 1\n\n$$a = 1, d = 2 - 1 = 1$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\n$$S_{12} = \\frac{12}{2}[2(1) + (12-1)(1)]$$\n\n$$= 6(2+11)$$\n\n$$= 6(13)$$\n\n$$= 78$$\n\nHence, the trees planted by the students of each section = 78\n\nThere for the trees planted by the students of 3 sections =  $78 \\times 3 = 234$\n\n18. A spiral is made up of successive semicircles, with centres alternately at A and B, starting with centre at A, of radii 0.5 cm, 1.0 cm, 1.5 cm, 2.0 cm, ... as shown in Fig. 1.4. What is the total length of such a spiral made up of thirteen consecutive semi circles (Take  $\\pi = \\frac{22}{7}$ )\n\n[Hint: length of successive semi circles is  $l_1, l_2, l_3, l_4$  ... with centers at A, B, A, B ...]\n\n$$\\text{The length of the semi circles} = \\pi r; l_1 = \\pi(0.5) = \\frac{\\pi}{2} \\text{ cm}; l_2 = \\pi(1) = \\pi \\text{ cm}; l_3 = \\pi(1.5) = \\frac{3\\pi}{2}$$\n\n![Diagram showing a spiral made up of successive semicircles, starting from center A, alternating between centers A and B. The radii of the semicircles are labeled l1, l2, l3, l4, etc.](b570812e4fe75e47d3e8905f839dc20c_img.jpg)\n\nDiagram showing a spiral made up of successive semicircles, starting from center A, alternating between centers A and B. The radii of the semicircles are labeled l1, l2, l3, l4, etc.\n\n\u2234 The lengths of semicircles are  $\\frac{\\pi}{2}, \\pi, \\frac{3\\pi}{2}, 2\\pi, \\dots$\n\n$$d = l_2 - l_1 = \\pi - \\frac{\\pi}{2} = \\frac{\\pi}{2}; a = \\frac{\\pi}{2} \\text{ cm}$$\n\n$$S_n = \\frac{n}{2}[2a + (n-1)d]$$\n\nThe total length of such a spiral made up of thirteen consecutive semi circles =  $S_{13}$\n\n$$\\begin{aligned}S_{13} &= \\frac{13}{2} \\left[ 2 \\times \\frac{\\pi}{2} + (13 - 1) \\frac{\\pi}{2} \\right] \\\\&= \\frac{13}{2} [\\pi + 6\\pi] \\\\&= \\frac{13}{2} (7\\pi) \\\\&= \\frac{13}{2} \\times 7 \\times \\frac{22}{2} \\\\&= 143 \\text{ cm}\\end{aligned}$$\n\n19. 200 logs are stacked in the following manner: 20 logs in the bottom row, 19 in the next row, 18 in the row next to it and so on (see Fig. 1.5). In how many rows are the 200 logs placed and how many logs are in the top row?\n\n![Diagram showing 200 logs stacked in rows, decreasing by one log per row from bottom to top, forming a triangular shape.](a1fad9ca0c696e710c9a7ae5622401e4_img.jpg)\n\nDiagram showing 200 logs stacked in rows, decreasing by one log per row from bottom to top, forming a triangular shape.\n\nThe logs are in an AP: 20, 19, 18...\n\nwith  $a = 20$ ,  $d = a_2 - a_1 = 19 - 20 = -1$\n\n$$S_n = 200$$\n\n$$S_n = \\frac{n}{2} [2a + (n - 1)d]$$\n\n$$200 = \\frac{n}{2} [2(20) + (n - 1)(-1)]$$\n\n$$200 = \\frac{n}{2} [40 - n + 1]$$\n\n$$\\Rightarrow 400 = n(40 - n + 1)$$\n\n$$\\Rightarrow 400 = n(41 - n)$$\n\n$$\\Rightarrow 400 = 41n - n^2$$\n\n$$n^2 - 41n + 400 = 0$$\n\n$$n^2 - 16n - 25n + 400 = 0$$\n\n$$n(n - 16) - 25(n - 16) = 0$$\n\n$$(n - 16)(n - 25) = 0$$\n\n$$(n - 16) = 0 \\text{ or } n - 25 = 0$$\n\n$$n = 16 \\text{ or } n = 25$$\n\n$$a_n = a + (n - 1)d$$\n\n$$a_{16} = 20 + (16 - 1)(-1)$$\n\n$$a_{16} = 20 - 15 = 5$$\n\nSimilarly,\n\n$$a_{25} = 20 + (25 - 1)(-1) = 20 - 24$$\n\n$= -4$  (negative number is not possible)\n\nHence the number of rows is 16 and the number of logs in the top row is 5\n\n20. In a potato race, a bucket is placed at the starting point, which is 5 m from the first potato, and the other potatoes are placed 3 m apart in a straight line. There are ten potatoes in the line (see Fig. 5.6).\n\nA competitor starts from the bucket, picks up the nearest potato, runs back with it, drops it in the bucket, runs back to pick up the next potato, runs to the bucket to drop it in, and she continues in the same way until all the potatoes are in the bucket. What is the total distance the competitor has to run?\n\n[Hint: To pick up the first potato and the second potato, the total distance (in metres) run by a competitor is  $2 \\times 5 + 2 \\times (5 + 3)$  ]\n\n![Diagram showing a bucket, a competitor running, and potatoes placed at distances 5m, 3m, 3m, 3m, 3m, 3m, 3m, 3m, 3m, 3m from the bucket.](eadd8abb2c85161842bcd823881cbe5f_img.jpg)\n\nDiagram showing a bucket, a competitor running, and potatoes placed at distances 5m, 3m, 3m, 3m, 3m, 3m, 3m, 3m, 3m, 3m from the bucket.\n\nThe distances from the bucket to potatoes 5,8,11,14 ...\n\nThey have to run twice, then the distances run by the competitor 10,16,22,28,34, ... ... ...\n\n$$a = 10, d = 16 - 10 = 6, S_{10} = ?$$\n\n$$S_n = \\frac{n}{2}[2a + (n - 1)d]$$\n\n$$S_{10} = \\frac{10}{2}[2(10) + (10 - 1)(6)]$$\n\n$$= 5[20 + 54]$$\n\n$$= 5(74)$$\n\n$$= 370$$\n\nHence, the distance the competitor has to run is 370 km\n\n"
    },
    {
      "section_id": 12,
      "section_type": "example",
      "title": "Exercise 5.3: Sums with a Given Last Term",
      "renderer": "manim",
      "narration": {
        "full_text": "Now for the second set of problems. Here, we are given the first and the last term, but not the number of terms. Think of it like a crowded street in Bangalore during rush hour; you see the first vehicle and the last one, but you need to figure out how many are in between! First, we must find 'n', the number of terms. For our first example, the series is 7, 10 and a half, 14, up to 84. We use the nth term formula, `l = a + (n-1)d`. Let's see it in action. We substitute `a=7`, `l=84`, and `d=7/2`. Solving this equation step-by-step, we find that 'n' is 23. So there are 23 terms in this AP. Now that we know 'n', we can find the sum. Since we know the last term, we can use a simpler formula: `S_n = n/2(a+l)`. This is a great shortcut! Let's watch the calculation. We plug in `n=23`, `a=7`, and `l=84`. This gives us 23 by 2 times 91, which equals 2093 by 2, or 1046 and a half. Great! Let's practice with a decreasing series: 34, 32, 30, down to 10. The common difference 'd' is -2. First, we find 'n'. Using the `l = a + (n-1)d` formula, we find that n is 13. Then, we use our sum formula `S_n = n/2(a+l)` to get the final sum, which is 286. Lastly, let's try one with all negative numbers. The series is -5, -8, -11, all the way to -230. The method is the same. First, find 'n' using the last term formula. 'n' comes out to be 76. Then, we calculate the sum `S_76`. Plugging in the values, we get 38 times -235, which results in a final sum of -8930. See? The same two steps work every time for this type of problem.",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Now for the second set of problems. Here, we are given the first and the last term, but not the number of terms. Think of it like a crowded street in Bangalore during rush hour; you see the first vehicle and the last one, but you need to figure out how many are in between! First, we must find 'n', the number of terms.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "For our first example, the series is 7, 10 and a half, 14, up to 84. We use the nth term formula, `l = a + (n-1)d`. Let's see it in action.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "We substitute `a=7`, `l=84`, and `d=7/2`. Solving this equation step-by-step, we find that 'n' is 23. So there are 23 terms in this AP.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Now that we know 'n', we can find the sum. Since we know the last term, we can use a simpler formula: `S_n = n/2(a+l)`. This is a great shortcut! Let's watch the calculation.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "We plug in `n=23`, `a=7`, and `l=84`. This gives us 23 by 2 times 91, which equals 2093 by 2, or 1046 and a half. Great!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "Let's practice with a decreasing series: 34, 32, 30, down to 10. The common difference 'd' is -2.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "First, we find 'n'. Using the `l = a + (n-1)d` formula, we find that n is 13. Then, we use our sum formula `S_n = n/2(a+l)` to get the final sum, which is 286.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "Lastly, let's try one with all negative numbers. The series is -5, -8, -11, all the way to -230. The method is the same.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_9",
            "text": "First, find 'n' using the last term formula. 'n' comes out to be 76. Then, we calculate the sum `S_76`. Plugging in the values, we get 38 times -235, which results in a final sum of -8930. See? The same two steps work every time for this type of problem.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "2. Find the sums given below",
            "end_phrase": "14 + \\dots + 84 \\quad \\text{ii) } 34"
          },
          "display_text": "2. Find the sums given below :\n\n$$\\text{i) } 7 + 10\\frac{1}{2} + 14 + \\dots + 84$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$\\text{i) } 7 + 10\\frac{1}{2} +",
            "end_phrase": "$$\\mathbf{n = 23}$$"
          },
          "display_text": "First, find n:\n$$l = a + (n - 1)d$$\n$$84 = 7 + (n - 1) \\times \\frac{7}{2}$$\n$$7n = 161$$\n$$\\mathbf{n = 23}$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_4",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$S_n = \\frac{n}{2}(a + l)$$",
            "end_phrase": "$$= 1046\\frac{1}{2}$$"
          },
          "display_text": "Now, find S_n:\n$$S_n = \\frac{n}{2}(a + l)$$\n$$S_{23} = \\frac{23}{2}(7 + 84)$$\n$$= 1046\\frac{1}{2}$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$\\text{ii) } 34 + 32 + 30",
            "end_phrase": "$$S_{13} = 286$$"
          },
          "display_text": "ii) 34 + 32 + 30 + ... + 10\nFirst find n: n = 13\nThen find S_n:\n$$S_{13} = \\frac{13}{2}(34 + 10) = 286$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_8",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "$$\\text{iii) } -5 + (-8) +",
            "end_phrase": "$$S_{76} &= -8930\\end{aligned}$$"
          },
          "display_text": "iii) -5 + (-8) + ... + (-230)\nFirst find n: n = 76\nThen find S_n:\n$$S_{76} = \\frac{76}{2} [(-5) + (-230)] = -8930$$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "This scene animates a two-step process. First, the formula `l = a + (n-1)d` appears. For problem (i), the values `a=7`, `l=84`, `d=7/2` are substituted and the equation solves for `n=23`, which is highlighted. Then, the scene transitions. The formula `S_n = n/2(a+l)` appears. The now-known `n=23` flies into place, along with `a` and `l`. The sum is calculated step-by-step, arriving at `1046.5`. This two-step animation\u2014first finding `n`, then finding `S_n`\u2014repeats for the other two sub-problems. For the decreasing series, numbers will visibly shrink, and for the negative series, the numbers will have a cool blue hue to emphasize their sign. The visuals are dynamic, with numbers moving and transforming to illustrate the calculations clearly.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.3: Sums with a Given Last Term\", font_size=36).to_edge(UP)\n        subtitle = Text(\"Step 1: Find n, Step 2: Find Sum\", font_size=28, color=YELLOW).next_to(title, DOWN)\n        self.play(Write(title), run_time=2.0)\n        self.play(FadeIn(subtitle), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(subtitle), run_time=0.5)\n        problem1 = Text(\"Problem (i): 7, 10.5, 14, ..., 84\", font_size=30).next_to(title, DOWN, buff=0.5)\n        formula_n = MathTex(\"l = a + (n-1)d\", font_size=40).shift(UP*0.5)\n        self.play(Write(problem1), run_time=1.5)\n        self.play(Write(formula_n), run_time=2.0)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        step1 = MathTex(\"84 = 7 + (n-1)\\\\times\\\\frac{7}{2}\", font_size=36).next_to(formula_n, DOWN, buff=0.5)\n        step2 = MathTex(\"77 = (n-1)\\\\times\\\\frac{7}{2}\", font_size=36).next_to(step1, DOWN, buff=0.3)\n        step3 = MathTex(\"n = 23\", font_size=40, color=GREEN).next_to(step2, DOWN, buff=0.3)\n        self.play(Write(step1), run_time=1.5)\n        self.play(Write(step2), run_time=1.5)\n        self.play(Write(step3), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(formula_n, step1, step2), run_time=0.8)\n        formula_sum = MathTex(\"S_n = \\\\frac{n}{2}(a+l)\", font_size=40).shift(UP*0.5)\n        highlight = Text(\"Shortcut Formula!\", font_size=28, color=YELLOW).next_to(formula_sum, DOWN, buff=0.3)\n        self.play(Write(formula_sum), run_time=2.0)\n        self.play(FadeIn(highlight), run_time=1.2)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(highlight, step3), run_time=0.5)\n        calc1 = MathTex(\"S_{23} = \\\\frac{23}{2}(7+84)\", font_size=36).next_to(formula_sum, DOWN, buff=0.4)\n        calc2 = MathTex(\"= \\\\frac{23}{2}\\\\times 91\", font_size=36).next_to(calc1, DOWN, buff=0.3)\n        calc3 = MathTex(\"= \\\\frac{2093}{2} = 1046.5\", font_size=40, color=GREEN).next_to(calc2, DOWN, buff=0.3)\n        self.play(Write(calc1), run_time=1.5)\n        self.play(Write(calc2), run_time=1.5)\n        self.play(Write(calc3), run_time=1.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        self.play(FadeOut(problem1, formula_sum, calc1, calc2, calc3), run_time=1.0)\n        problem2 = Text(\"Problem (ii): 34, 32, 30, ..., 10\", font_size=30).next_to(title, DOWN, buff=0.5)\n        note = Text(\"d = -2 (decreasing)\", font_size=26, color=ORANGE).next_to(problem2, DOWN, buff=0.3)\n        self.play(Write(problem2), run_time=2.0)\n        self.play(FadeIn(note), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(note), run_time=0.5)\n        find_n2 = MathTex(\"10 = 34 + (n-1)(-2) \\\\Rightarrow n = 13\", font_size=34, color=GREEN).shift(UP*0.3)\n        sum_calc2 = MathTex(\"S_{13} = \\\\frac{13}{2}(34+10) = \\\\frac{13}{2}\\\\times 44 = 286\", font_size=34, color=GREEN).next_to(find_n2, DOWN, buff=0.5)\n        self.play(Write(find_n2), run_time=2.0)\n        self.play(Write(sum_calc2), run_time=2.5)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.50s\n        # Segment 8 (35.0s - 40.0s, duration 5.0s)\n        self.play(FadeOut(problem2, find_n2, sum_calc2), run_time=1.0)\n        problem3 = Text(\"Problem (iii): -5, -8, -11, ..., -230\", font_size=30, color=BLUE).next_to(title, DOWN, buff=0.5)\n        note3 = Text(\"All negative numbers\", font_size=26, color=TEAL).next_to(problem3, DOWN, buff=0.3)\n        self.play(Write(problem3), run_time=2.0)\n        self.play(FadeIn(note3), run_time=1.5)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 6.00s\n        # Segment 9 (40.0s - 45.0s, duration 5.0s)\n        self.play(FadeOut(note3), run_time=0.5)\n        find_n3 = MathTex(\"-230 = -5 + (n-1)(-3) \\\\Rightarrow n = 76\", font_size=32, color=GREEN).shift(UP*0.3)\n        sum_calc3 = MathTex(\"S_{76} = \\\\frac{76}{2}(-5-230) = 38\\\\times(-235) = -8930\", font_size=32, color=GREEN).next_to(find_n3, DOWN, buff=0.5)\n        self.play(Write(find_n3), run_time=2.0)\n        self.play(Write(sum_calc3), run_time=2.0)\n        self.wait(1.0)\n        # Hard Sync WARNING: Animation exceeds audio by 5.50s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      }
    },
    {
      "section_id": 13,
      "section_type": "example",
      "title": "Exercise 5.3: Finding Missing Information",
      "renderer": "manim",
      "narration": {
        "full_text": "In our final section, we become mathematical detectives! We are given a few clues about an AP, and we need to find the missing values. Let's look at the first case: we are given `a=5`, `d=3`, and the nth term `a_n=50`. We need to find 'n' and the sum `S_n`. Let's see the animation. First, we use the `a_n` formula to find 'n'. Plugging in the values, we solve and find `n=16`. Now that we have 'n', we can easily find the sum `S_16` using the formula `S_n = n/2(a+a_n)`. The sum is 440. Simple, right? Now for a trickier case. We're given the 3rd term is 15 and the sum of the first 10 terms is 125. We need to find 'd' and the 10th term. This requires setting up two simultaneous equations. Watch carefully. From `a_3=15`, we get our first equation: `a + 2d = 15`. From `S_10=125`, we get our second equation: `2a + 9d = 25`. The animation will now solve these two equations together. We find that `d = -1` and `a = 17`. With these, we can find any term! The 10th term, `a_10`, is 8. Let's tackle one more. We're given `a_n=4`, `d=2`, and `S_n=-14`. We need to find 'n' and 'a'. This one leads to a quadratic equation. First, we express 'a' in terms of 'n' using the `a_n` formula, which gives us `a = 6 - 2n`. Now, we substitute this into the `S_n` formula. This simplifies into a quadratic equation: `n^2 - 5n - 14 = 0`. Solving this, we get two possible values for n: 7 and -2. Since 'n' must be a positive integer, we choose `n=7`. Finally, we find 'a' by substituting n=7 back into our expression for 'a', which gives us `a = -8`. Fantastic work!",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "In our final section, we become mathematical detectives! We are given a few clues about an AP, and we need to find the missing values.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "Let's look at the first case: we are given `a=5`, `d=3`, and the nth term `a_n=50`. We need to find 'n' and the sum `S_n`. Let's see the animation.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "First, we use the `a_n` formula to find 'n'. Plugging in the values, we solve and find `n=16`. Now that we have 'n', we can easily find the sum `S_16` using the formula `S_n = n/2(a+a_n)`. The sum is 440. Simple, right?",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "Now for a trickier case. We're given the 3rd term is 15 and the sum of the first 10 terms is 125. We need to find 'd' and the 10th term. This requires setting up two simultaneous equations. Watch carefully.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "From `a_3=15`, we get our first equation: `a + 2d = 15`. From `S_10=125`, we get our second equation: `2a + 9d = 25`. The animation will now solve these two equations together. We find that `d = -1` and `a = 17`. With these, we can find any term! The 10th term, `a_10`, is 8.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "Let's tackle one more. We're given `a_n=4`, `d=2`, and `S_n=-14`. We need to find 'n' and 'a'. This one leads to a quadratic equation.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "First, we express 'a' in terms of 'n' using the `a_n` formula, which gives us `a = 6 - 2n`. Now, we substitute this into the `S_n` formula. This simplifies into a quadratic equation: `n^2 - 5n - 14 = 0`. Solving this, we get two possible values for n: 7 and -2. Since 'n' must be a positive integer, we choose `n=7`. Finally, we find 'a' by substituting n=7 back into our expression for 'a', which gives us `a = -8`. Fantastic work!",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "hide",
              "visual_layer": "show",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "text",
          "markdown_pointer": {
            "start_phrase": "3. In an AP:\n\ni) Given",
            "end_phrase": "find  $n$  and  $S_n$"
          },
          "display_text": "3. In an AP:\ni) Given  $a = 5$ ,  $d = 3$ ,  $a_n = 50$  find  $n$  and  $S_n$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "i) Given  $a = 5$ ,",
            "end_phrase": "$$S_{16} = 440$$"
          },
          "display_text": "Given $a=5, d=3, a_n=50$\n1. Find n: $50 = 5+(n-1)3 \\Rightarrow n=16$\n2. Find S_n: $S_{16} = \\frac{16}{2}(5+50) = 440$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_4",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "iv) Given  $a_3 = 15$ ,",
            "end_phrase": "$$a_{10} = 8$$"
          },
          "display_text": "iv) Given $a_3=15, S_{10}=125$\n1. Set up equations:\n   Eq1: $a+2d=15$\n   Eq2: $2a+9d=25$\n2. Solve: $d=-1, a=17$\n3. Find $a_{10}$: $a_{10} = 17 + (9)(-1) = 8$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "viii) Given  $a_n = 4$ ,",
            "end_phrase": "$$a = -8$$"
          },
          "display_text": "viii) Given $a_n=4, d=2, S_n=-14$\n1. Set up equations:\n   Eq1: $a = 6-2n$\n   Eq2: $-28 = n(a+4)$\n2. Substitute & Solve Quadratic:\n   $n^2-5n-14=0 \\Rightarrow (n-7)(n+2)=0 \\Rightarrow n=7$\n3. Find a: $a = 6-2(7) = -8$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": {
          "description": "The scene has a 'detective' theme, with magnifying glass icons appearing. For problem (i), the given clues `a=5, d=3, a_n=50` are shown. The formula `a_n=a+(n-1)d` is used to find `n=16`. Then, `S_n=n/2(a+a_n)` is used to find `S_n=440`. For problem (iv), two equation templates, `a +_d = _` and `_a + _d = _`, appear. Values from the clues `a_3=15` and `S_10=125` fly into the blanks, creating `a+2d=15` and `2a+9d=25`. The animation shows these equations aligning and subtracting to solve for `d=-1` and `a=17`. For problem (viii), substitution is animated by showing the expression `6-2n` literally replacing 'a' in the second equation, leading to a quadratic equation. The quadratic formula animation runs, revealing roots 7 and -2. The -2 root fades out as invalid, leaving `n=7`. This is plugged back to find `a=-8`.",
          "manim_code": "from manim import *\n\nclass MainScene(Scene):\n    def construct(self):\n        # Segment 1 (0.0s - 5.0s, duration 5.0s)\n        title = Text(\"Exercise 5.3: Finding Missing Information\", font_size=36).to_edge(UP)\n        magnifier = Circle(radius=0.5, color=YELLOW).shift(LEFT*3 + UP*0.5)\n        handle = Line(magnifier.get_bottom(), magnifier.get_bottom() + DOWN*0.8, color=YELLOW, stroke_width=8)\n        detective_icon = VGroup(magnifier, handle)\n        subtitle = Text(\"Mathematical Detectives!\", font_size=28, color=GOLD).next_to(detective_icon, RIGHT)\n        \n        self.play(Write(title), run_time=1.5)\n        self.play(Create(detective_icon), Write(subtitle), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 2 (5.0s - 10.0s, duration 5.0s)\n        self.play(FadeOut(detective_icon), FadeOut(subtitle), run_time=0.5)\n        \n        problem1_title = Text(\"Problem (i)\", font_size=30, color=BLUE).next_to(title, DOWN, buff=0.5)\n        given1 = VGroup(\n            Text(\"Given: a=5, d=3, a_n=50\", font_size=24),\n            Text(\"Find: n and S_n\", font_size=24, color=GREEN)\n        ).arrange(DOWN, aligned_edge=LEFT).next_to(problem1_title, DOWN, buff=0.3)\n        \n        self.play(Write(problem1_title), run_time=1.0)\n        self.play(Write(given1), run_time=2.5)\n        self.wait(1.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 3 (10.0s - 15.0s, duration 5.0s)\n        formula1 = MathTex(\"a_n = a + (n-1)d\", font_size=32).shift(DOWN*0.5)\n        substitution1 = MathTex(\"50 = 5 + (n-1) \\\\times 3\", font_size=32).next_to(formula1, DOWN, buff=0.3)\n        solution_n = MathTex(\"n = 16\", font_size=36, color=YELLOW).next_to(substitution1, DOWN, buff=0.3)\n        \n        self.play(FadeOut(given1), run_time=0.3)\n        self.play(Write(formula1), run_time=1.0)\n        self.play(Write(substitution1), run_time=1.0)\n        self.play(Write(solution_n), run_time=0.8)\n        \n        sum_formula = MathTex(\"S_n = \\\\frac{n}{2}(a + a_n)\", font_size=28).shift(DOWN*2.5)\n        sum_result = MathTex(\"S_{16} = 440\", font_size=32, color=GREEN).next_to(sum_formula, DOWN, buff=0.2)\n        \n        self.play(Write(sum_formula), run_time=0.8)\n        self.play(Write(sum_result), run_time=0.6)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 4 (15.0s - 20.0s, duration 5.0s)\n        self.play(FadeOut(problem1_title, formula1, substitution1, solution_n, sum_formula, sum_result), run_time=0.5)\n        \n        problem2_title = Text(\"Problem (iv)\", font_size=30, color=BLUE).next_to(title, DOWN, buff=0.5)\n        given2 = VGroup(\n            Text(\"Given: a_3=15, S_10=125\", font_size=24),\n            Text(\"Find: d and a_10\", font_size=24, color=GREEN)\n        ).arrange(DOWN, aligned_edge=LEFT).next_to(problem2_title, DOWN, buff=0.3)\n        \n        self.play(Write(problem2_title), run_time=1.0)\n        self.play(Write(given2), run_time=1.5)\n        self.wait(2.0)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 5 (20.0s - 25.0s, duration 5.0s)\n        self.play(FadeOut(given2), run_time=0.3)\n        \n        eq1 = MathTex(\"a + 2d = 15\", font_size=30, color=YELLOW).shift(UP*0.5)\n        eq2 = MathTex(\"2a + 9d = 25\", font_size=30, color=YELLOW).next_to(eq1, DOWN, buff=0.4)\n        \n        self.play(Write(eq1), run_time=1.0)\n        self.play(Write(eq2), run_time=1.0)\n        \n        solution_d = MathTex(\"d = -1\", font_size=32, color=GREEN).shift(DOWN*1.5 + LEFT*2)\n        solution_a = MathTex(\"a = 17\", font_size=32, color=GREEN).next_to(solution_d, RIGHT, buff=1.0)\n        \n        self.play(Write(solution_d), Write(solution_a), run_time=1.2)\n        \n        a10_result = MathTex(\"a_{10} = 8\", font_size=36, color=ORANGE).shift(DOWN*2.5)\n        self.play(Write(a10_result), run_time=1.0)\n        self.wait(0.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 6 (25.0s - 30.0s, duration 5.0s)\n        self.play(FadeOut(problem2_title, eq1, eq2, solution_d, solution_a, a10_result), run_time=0.5)\n        \n        problem3_title = Text(\"Problem (viii)\", font_size=30, color=BLUE).next_to(title, DOWN, buff=0.5)\n        given3 = VGroup(\n            Text(\"Given: a_n=4, d=2, S_n=-14\", font_size=24),\n            Text(\"Find: n and a\", font_size=24, color=GREEN)\n        ).arrange(DOWN, aligned_edge=LEFT).next_to(problem3_title, DOWN, buff=0.3)\n        \n        self.play(Write(problem3_title), run_time=1.0)\n        self.play(Write(given3), run_time=2.0)\n        self.wait(1.5)\n        \n        # Hard Sync WARNING: Animation exceeds audio by 5.00s\n        # Segment 7 (30.0s - 35.0s, duration 5.0s)\n        self.play(FadeOut(given3), run_time=0.3)\n        \n        expr_a = MathTex(\"a = 6 - 2n\", font_size=28, color=YELLOW).shift(UP*1.0)\n        self.play(Write(expr_a), run_time=0.8)\n        \n        quadratic = MathTex(\"n^2 - 5n - 14 = 0\", font_size=32, color=ORANGE).next_to(expr_a, DOWN, buff=0.4)\n        self.play(Write(quadratic), run_time=1.0)\n        \n        roots = MathTex(\"n = 7 \\\\text{ or } n = -2\", font_size=28).next_to(quadratic, DOWN, buff=0.4)\n        self.play(Write(roots), run_time=1.0)\n        \n        final_n = MathTex(\"n = 7\", font_size=32, color=GREEN).shift(DOWN*1.5 + LEFT*2)\n        final_a = MathTex(\"a = -8\", font_size=32, color=GREEN).next_to(final_n, RIGHT, buff=1.5)\n        \n        self.play(Write(final_n), run_time=0.8)\n        self.play(Write(final_a), run_time=0.8)\n        self.wait(0.3)\n        # Hard Sync WARNING: Animation exceeds audio by 5.00s",
          "code_type": "construct_body"
        },
        "video_prompts": []
      }
    },
    {
      "section_id": 14,
      "section_type": "content",
      "title": "Summary of Arithmetic Progressions",
      "renderer": "none",
      "narration": {
        "full_text": "Alright, let's quickly summarize what we've learned about Arithmetic Progressions. First, remember that an AP is a sequence where each new term is found by adding a fixed number, which we call 'd' or the common difference, to the one before it. The general form of an AP is a, a plus d, a plus 2d, and so on. Think of it like a series of steps, each one the same size. Now, if the progression has a clear end point, like the number of stops on a bus route in Bangalore, we call it a finite AP. It has a last term. But if it goes on forever, like the traffic itself, with no end in sight, it's an infinite AP. Such APs do not have a last term. To find any term in the sequence, the nth term, we use the formula a_n equals a plus (n minus 1)d. And if you need to find a term starting from the end of a finite AP, the formula is l minus (n minus 1)d, where 'l' is the last term. When you need to add up a series of terms, we have two formulas for the sum. The first is S equals n by 2, times the quantity 2a plus (n minus 1)d. This is useful when you know the first term and the common difference. But if you don't know the common difference and you know the last term, there's a simpler formula: S equals n by 2 times (a plus l). Keep these points in mind, and you'll master APs in no time!",
        "segments": [
          {
            "segment_id": "seg_1",
            "text": "Alright, let's quickly summarize what we've learned about Arithmetic Progressions. First, remember that an AP is a sequence where each new term is found by adding a fixed number, which we call 'd' or the common difference, to the one before it.",
            "purpose": "introduce",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_2",
            "text": "The general form of an AP is a, a plus d, a plus 2d, and so on. Think of it like a series of steps, each one the same size.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_3",
            "text": "Now, if the progression has a clear end point, like the number of stops on a bus route in Bangalore, we call it a finite AP. It has a last term.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_4",
            "text": "But if it goes on forever, like the traffic itself, with no end in sight, it's an infinite AP. Such APs do not have a last term.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_5",
            "text": "To find any term in the sequence, the nth term, we use the formula a_n equals a plus (n minus 1)d.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_6",
            "text": "And if you need to find a term starting from the end of a finite AP, the formula is l minus (n minus 1)d, where 'l' is the last term.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_7",
            "text": "When you need to add up a series of terms, we have two formulas for the sum. The first is S equals n by 2, times the quantity 2a plus (n minus 1)d. This is useful when you know the first term and the common difference.",
            "purpose": "explain",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          },
          {
            "segment_id": "seg_8",
            "text": "But if you don't know the common difference and you know the last term, there's a simpler formula: S equals n by 2 times (a plus l). Keep these points in mind, and you'll master APs in no time!",
            "purpose": "conclude",
            "display_directives": {
              "text_layer": "show",
              "visual_layer": "hide",
              "avatar_layer": "show"
            }
          }
        ]
      },
      "visual_beats": [
        {
          "beat_id": "beat_1",
          "segment_id": "seg_1",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "- An arithmetic progression (AP) is",
            "end_phrase": "is called the common difference"
          },
          "display_text": "- An arithmetic progression (AP) is a list of numbers in which each term is obtained by adding a fixed number d to the preceding term, except the first term. The fixed number d is called the common difference",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_2",
          "segment_id": "seg_2",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "- The general form of an",
            "end_phrase": "AP :  $a, a + d, a + 2d, a + 3d, \\dots$"
          },
          "display_text": "- The general form of an AP :  $a, a + d, a + 2d, a + 3d, \\dots$",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_3",
          "segment_id": "seg_3",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "- In an AP if there",
            "end_phrase": "AP has a last term."
          },
          "display_text": "- In an AP if there are only a finite number of terms. Such an AP is called a finite AP. Such AP has a last term.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_4",
          "segment_id": "seg_4",
          "visual_type": "bullet_list",
          "markdown_pointer": {
            "start_phrase": "- The AP has infinite number",
            "end_phrase": "have a last term."
          },
          "display_text": "- The AP has infinite number of terms is called infinite Arithmetic Progression. Such APs do not have a last term.",
          "latex_content": null,
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_5",
          "segment_id": "seg_5",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "- The first term -  $a$",
            "end_phrase": "$$a_n = a + (n - 1)d$$"
          },
          "display_text": "- The first term -  $a$  and the common difference is  $d$  then the  $n$ th term of an AP\n\n$$a_n = a + (n - 1)d$$",
          "latex_content": "a_n = a + (n - 1)d",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_6",
          "segment_id": "seg_6",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "- The  $n$ th term from",
            "end_phrase": "$$l - (n - 1)d$$"
          },
          "display_text": "- The  $n$ th term from the last [ last term -1, common difference - $d$  ]\n\n$$l - (n - 1)d$$",
          "latex_content": "l - (n - 1)d",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_7",
          "segment_id": "seg_7",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "- $a$  is the first term,",
            "end_phrase": "$$S = \\frac{n}{2}[2a + (n - 1)d]$$"
          },
          "display_text": "- $a$  is the first term,  $d$  is the common difference then sum to  $n$ th term\n\n$$S = \\frac{n}{2}[2a + (n - 1)d]$$",
          "latex_content": "S = \\frac{n}{2}[2a + (n - 1)d]",
          "image_id": null,
          "answer_revealed": false
        },
        {
          "beat_id": "beat_8",
          "segment_id": "seg_8",
          "visual_type": "equation",
          "markdown_pointer": {
            "start_phrase": "- If common difference is unknown",
            "end_phrase": "$$S = \\frac{n}{2}[a + l] \\{l - \\text{the last term}\\}$$"
          },
          "display_text": "- If common difference is unknown then the sum to  $n$ th term\n\n$$S = \\frac{n}{2}[a + l] \\{l - \\text{the last term}\\}$$",
          "latex_content": "S = \\frac{n}{2}[a + l]",
          "image_id": null,
          "answer_revealed": false
        }
      ],
      "render_spec": {
        "manim_scene_spec": null,
        "video_prompts": []
      },
      "content": "## Summary:\n\n- An arithmetic progression (AP) is a list of numbers in which each term is obtained by adding a fixed number  $d$  to the preceding term, except the first term. The fixed number  $d$  is called the common difference\n- The general form of an AP :  $a, a + d, a + 2d, a + 3d, \\dots$\n- In an AP if there are only a finite number of terms. Such an AP is called a finite AP. Such AP has a last term.\n- The AP has infinite number of terms is called infinite Arithmetic Progression. Such APs do not have a last term.\n- The first term -  $a$  and the common difference is  $d$  then the  $n$ th term of an AP\n\n$$a_n = a + (n - 1)d$$\n\n- The  $n$ th term from the last [ last term -1, common difference - $d$  ]\n\n$$l - (n - 1)d$$\n\n- $a$  is the first term,  $d$  is the common difference then sum to  $n$ th term\n\n$$S = \\frac{n}{2}[2a + (n - 1)d]$$\n\n- If common difference is unknown then the sum to  $n$ th term\n\n$$S = \\frac{n}{2}[a + l] \\{l - \\text{the last term}\\}$$"
    },
    {
      "section_id": 15,
      "section_type": "memory",
      "title": "Key Concepts",
      "renderer": "none",
      "flashcards": [
        {
          "front": "What is the defining feature of an Arithmetic Progression (AP)?",
          "back": "A Constant Difference! Each term is found by adding a fixed number (the Common Difference, 'd') to the one before it. Think: Consistent Development."
        },
        {
          "front": "How can you find the 100th term of an AP without listing all 100 terms?",
          "back": "Use the formula: a_n = a + (n-1)d. Mnemonic: 'Any Number is Discovered' from the first term 'a' and common difference 'd'."
        },
        {
          "front": "Can the common difference 'd' be negative or zero?",
          "back": "Yes! A positive 'd' means the sequence increases. A negative 'd' means it decreases. A zero 'd' means all the terms are the same."
        },
        {
          "front": "What's the shortcut to find the sum of an AP if you know the first (a) and last (l) terms?",
          "back": "Use S = n/2 * (a + l). Mnemonic: 'Sum = Number of terms / 2 times (Alpha + Last)'. It's the average of the first and last term, times the number of terms."
        },
        {
          "front": "What is the difference between a Finite AP and an Infinite AP?",
          "back": "A Finite AP has a Finish line (a last term). An Infinite AP goes on Indefinitely (no last term). One has an end, the other doesn't."
        }
      ],
      "narration": {
        "full_text": "Let's reinforce what we've learned. We'll use some quick flashcards to test your memory on the key concepts of Arithmetic Progression. Try to answer the question before the reveal!",
        "segments": [
          {
            "purpose": "introduce",
            "start_time": 0,
            "end_time": 8,
            "text": "Let's reinforce what we've learned. We'll use some quick flashcards to test your memory on the key concepts of Arithmetic Progression. Try to answer the question before the reveal!"
          }
        ]
      }
    },
    {
      "section_id": 16,
      "section_type": "recap",
      "title": "Lesson Recap",
      "renderer": "wan_video",
      "text_layer": "hide",
      "visual_layer": "show",
      "video_prompts": [
        {
          "prompt": "Cinematic, slow-motion shot. A young girl in a vibrant green paddy field in a Kerala village. The camera, low to the ground, tracks alongside her as she walks, her fingers lightly brushing against the tops of evenly spaced coconut trees lining the path. The lighting is the golden hour of early morning, creating long shadows and a warm, nostalgic glow. The texture of the palm leaves and the rich, dark soil is highly detailed. The mood is one of discovery and wonder, as she notices the repeating pattern of the trees.",
          "start_time": 0,
          "end_time": 15
        },
        {
          "prompt": "Transition to a bustling, modern classroom in Mumbai. The camera pans across the faces of diverse students, finally focusing on a large, interactive whiteboard. A teacher's hand writes the definition: 'An arithmetic progression is a list of numbers in which each term is obtained by adding a fixed number...' The numbers '100, 150, 200, 250...' appear below, glowing softly. The lighting is bright and clean. The mood is focused and academic, emphasizing the formalization of the initial observation.",
          "start_time": 15,
          "end_time": 30
        },
        {
          "prompt": "Dynamic drone shot, flying over a vast, lush tea plantation in Assam. The rows of tea bushes are perfectly geometric. The video freeze-frames, and a graphical overlay appears, highlighting one row. The formula 'a_n = a + (n-1)d' materializes on screen, with 'n' animating to show the calculation for a distant row. The color palette is dominated by intense greens and earthy browns. The mood is expansive and applicative, showing the concept's power to predict.",
          "start_time": 30,
          "end_time": 45
        },
        {
          "prompt": "A close-up shot of a piggy bank in a teenager's room in a Delhi apartment. The background shows a vibrant, busy street scene through the window. Hands are seen dropping coins and bills into the piggy bank. A calendar on the wall has amounts circled each month: \u20b950, \u20b9100, \u20b9150. The sum formula 'S = n/2 [2a + (n-1)d]' overlays the scene, calculating the total savings. The lighting is warm and personal. The mood is aspirational and practical, connecting the math to personal goals.",
          "start_time": 45,
          "end_time": 60
        },
        {
          "prompt": "Final scene in a sleek, modern office in a Hyderabad tech park. A young professional, the same student from the start but now older, points to a graph on a large screen showing production output over time. The graph shows a clear linear increase. The line is an Arithmetic Progression. The camera pulls back to show her collaborating with a diverse team. The lighting is cool and professional, with blue and white tones. The mood is confident and forward-looking, showing AP as a tool for future success.",
          "start_time": 60,
          "end_time": 75
        }
      ],
      "narration": {
        "full_text": "We started our journey by observing patterns in the world around us, like trees in a row. These patterns of steady change are everywhere. We then gave this pattern a name: Arithmetic Progression, defined by a first term and a constant difference that is added to get the next term. We learned the powerful formula to find any term in the sequence, which allows us to predict values far down the line without listing them all. Next, we discovered how to calculate the total sum of these terms, a useful skill for tracking growth, like with savings over time. Finally, we saw how this simple idea scales up, becoming a fundamental tool for analyzing trends and making predictions in real-world scenarios, from agriculture to technology.",
        "segments": [
          {
            "purpose": "recap",
            "start_time": 0,
            "end_time": 15,
            "text": "We started our journey by observing patterns in the world around us, like trees in a row. These patterns of steady change are everywhere."
          },
          {
            "purpose": "recap",
            "start_time": 15,
            "end_time": 30,
            "text": "We then gave this pattern a name: Arithmetic Progression, defined by a first term and a constant difference that is added to get the next term."
          },
          {
            "purpose": "recap",
            "start_time": 30,
            "end_time": 45,
            "text": "We learned the powerful formula to find any term in the sequence, which allows us to predict values far down the line without listing them all."
          },
          {
            "purpose": "recap",
            "start_time": 45,
            "end_time": 60,
            "text": "Next, we discovered how to calculate the total sum of these terms, a useful skill for tracking growth, like with savings over time."
          },
          {
            "purpose": "recap",
            "start_time": 60,
            "end_time": 75,
            "text": "Finally, we saw how this simple idea scales up, becoming a fundamental tool for analyzing trends and making predictions in real-world scenarios, from agriculture to technology."
          }
        ]
      },
      "renderer_override_reason": "Recap sections use WAN for storyboard visualization"
    }
  ],
  "metadata": {
    "generated_by": "v2.5-partition-director",
    "doc_length": 54786,
    "chunks": 6,
    "llm_calls": 8,
    "generation_scope": "full",
    "pipeline_mode": "v2.5-partition-conquer",
    "total_sections": 16
  },
  "avatar_global": {
    "style": "teacher",
    "default_position": "right",
    "default_width_percent": 52,
    "gesture_enabled": true
  }
}